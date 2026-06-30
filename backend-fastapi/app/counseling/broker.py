import asyncio
import json
import uuid
from typing import Optional
import redis.asyncio as redis
from fastapi import WebSocket
import structlog

logger = structlog.get_logger(__name__)


class TurnHoldManager:
    """
    Manages turn-holding and reflection window state.
    """
    REFLECTION_WINDOW_SECONDS = 10

    def __init__(self, broker: "JointSessionBroker"):
        self.broker = broker

    async def activate_window(self, session_id: str, user_id: str):
        """
        Activates reflection window for user_id in session_id.
        """
        redis_key = f"reflection_window:{session_id}:{user_id}"
        await self.broker.redis.setex(redis_key, self.REFLECTION_WINDOW_SECONDS, "active")
        
        # Schedule the expiration resolution task
        asyncio.create_task(self._wait_and_resolve(session_id, user_id))

    async def is_window_active(self, session_id: str, user_id: str) -> bool:
        redis_key = f"reflection_window:{session_id}:{user_id}"
        return await self.broker.redis.exists(redis_key) > 0

    async def get_remaining_seconds(self, session_id: str, user_id: str) -> int:
        redis_key = f"reflection_window:{session_id}:{user_id}"
        ttl = await self.broker.redis.ttl(redis_key)
        return max(0, ttl)

    async def clear_window(self, session_id: str, user_id: str):
        redis_key = f"reflection_window:{session_id}:{user_id}"
        await self.broker.redis.delete(redis_key)

    async def queue_message(self, session_id: str, user_id: str, content: str):
        redis_key = f"queued_message:{session_id}:{user_id}"
        await self.broker.redis.set(redis_key, content)

    async def get_queued_message(self, session_id: str, user_id: str) -> Optional[str]:
        redis_key = f"queued_message:{session_id}:{user_id}"
        return await self.broker.redis.get(redis_key)

    async def clear_queued_message(self, session_id: str, user_id: str):
        redis_key = f"queued_message:{session_id}:{user_id}"
        await self.broker.redis.delete(redis_key)

    async def _wait_and_resolve(self, session_id: str, user_id: str):
        await asyncio.sleep(self.REFLECTION_WINDOW_SECONDS)
        # Check if still exists and active (might have been cleared early or replaced)
        if await self.is_window_active(session_id, user_id):
            await self.clear_window(session_id, user_id)
            
            # Send turn start to user
            await self.broker.send_to_user(session_id, user_id, {
                "type": "turn_start",
                "your_turn": True
            })
            
            # If there was a queued message, deliver it now
            queued = await self.get_queued_message(session_id, user_id)
            if queued:
                await self.clear_queued_message(session_id, user_id)
                # Broadcast the queued message to the session
                # In a real pipeline, this would re-route to LLM, here we simulate broadcasting it
                await self.broker.broadcast_to_session(session_id, {
                    "type": "partner_message_original",
                    "content": queued
                })


class JointSessionBroker:
    """
    Manages WebSocket connections for joint counseling sessions and uses
    Redis Pub/Sub to synchronize messages across multiple backend instances.
    """

    def __init__(self, redis_url: str):
        self.redis = redis.from_url(redis_url, decode_responses=True)
        self.pod_id = str(uuid.uuid4())
        # Mapping from session_id to a list of connected local WebSockets
        self.active_sessions: dict[str, list[WebSocket]] = {}
        # Mapping from (session_id, user_id) to the specific WebSocket instance
        self.user_connections: dict[tuple[str, str], WebSocket] = {}
        # Mapping from session_id to the asyncio Task listening to Redis Pub/Sub
        self.pubsub_tasks: dict[str, asyncio.Task] = {}
        self.turn_hold_manager = TurnHoldManager(self)

    async def connect(self, session_id: str, user_id: str, websocket: WebSocket):
        await websocket.accept()

        # Register local connection
        if session_id not in self.active_sessions:
            self.active_sessions[session_id] = []

            # Start pub/sub listener for the new session on this instance
            pubsub = self.redis.pubsub()
            await pubsub.subscribe(f"joint_session:{session_id}")
            task = asyncio.create_task(self._listen_to_redis(session_id, pubsub))
            self.pubsub_tasks[session_id] = task
            logger.info("subscribed_to_session_channel", session_id=session_id)

        self.active_sessions[session_id].append(websocket)
        self.user_connections[(session_id, user_id)] = websocket
        
        # Register connection in Redis
        await self.redis.set(f"ws_conn:{session_id}:{user_id}", self.pod_id)

        logger.info(
            "websocket_connected",
            session_id=session_id,
            user_id=user_id,
            active_connections=len(self.active_sessions[session_id]),
        )

    async def disconnect(self, session_id: str, user_id: str, websocket: WebSocket):
        # Remove from local registries
        if session_id in self.active_sessions:
            if websocket in self.active_sessions[session_id]:
                self.active_sessions[session_id].remove(websocket)
                logger.info(
                    "websocket_disconnected",
                    session_id=session_id,
                    user_id=user_id,
                    remaining_connections=len(self.active_sessions[session_id]),
                )

            if not self.active_sessions[session_id]:
                del self.active_sessions[session_id]
                if session_id in self.pubsub_tasks:
                    task = self.pubsub_tasks.pop(session_id)
                    task.cancel()
                logger.info("unsubscribed_from_session_channel", session_id=session_id)

        self.user_connections.pop((session_id, user_id), None)
        
        # Remove Redis connection key
        await self.redis.delete(f"ws_conn:{session_id}:{user_id}")

    async def broadcast_to_session(self, session_id: str, event: dict, exclude_user_id: Optional[str] = None):
        """
        Publishes event to Redis channel: joint_session:{session_id}
        """
        payload = json.dumps({
            "target_user_id": None,
            "exclude_user_id": exclude_user_id,
            "event": event
        })
        await self.redis.publish(f"joint_session:{session_id}", payload)

    async def send_to_user(self, session_id: str, user_id: str, event: dict):
        """
        Sends event to a specific user only.
        """
        ws = self.user_connections.get((session_id, user_id))
        if ws:
            try:
                await ws.send_text(json.dumps(event))
                return
            except Exception:
                pass
        
        payload = json.dumps({
            "target_user_id": user_id,
            "exclude_user_id": None,
            "event": event
        })
        await self.redis.publish(f"joint_session:{session_id}", payload)

    async def broadcast(self, session_id: str, message: dict):
        """
        Legacy broadcast method helper to map to broadcast_to_session
        """
        await self.broadcast_to_session(session_id, message)

    async def _listen_to_redis(self, session_id: str, pubsub: redis.client.PubSub):
        """
        Continuously listens for messages on the Redis Pub/Sub channel and
        broadcasts them to all locally connected websockets for this session.
        """
        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    data = json.loads(message["data"])
                    target_user_id = data.get("target_user_id")
                    exclude_user_id = data.get("exclude_user_id")
                    event = data.get("event")

                    for (s_id, u_id), ws in list(self.user_connections.items()):
                        if s_id == session_id:
                            if target_user_id and u_id != target_user_id:
                                continue
                            if exclude_user_id and u_id == exclude_user_id:
                                continue
                            try:
                                await ws.send_text(json.dumps(event))
                            except Exception:
                                pass
        except asyncio.CancelledError:
            await pubsub.unsubscribe(f"joint_session:{session_id}")
            await pubsub.close()
        except Exception as e:
            logger.error(
                "redis_pubsub_listener_error", session_id=session_id, error=str(e)
            )

