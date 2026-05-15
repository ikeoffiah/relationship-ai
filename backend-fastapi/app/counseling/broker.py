import asyncio
import json
import redis.asyncio as redis
from fastapi import WebSocket
import structlog

logger = structlog.get_logger(__name__)


class JointSessionBroker:
    """
    Manages WebSocket connections for joint counseling sessions and uses
    Redis Pub/Sub to synchronize messages across multiple backend instances.
    """

    def __init__(self, redis_url: str):
        self.redis = redis.from_url(redis_url, decode_responses=True)
        # Mapping from session_id to a list of connected local WebSockets
        self.active_sessions: dict[str, list[WebSocket]] = {}
        # Mapping from session_id to the asyncio Task listening to Redis Pub/Sub
        self.pubsub_tasks: dict[str, asyncio.Task] = {}

    async def connect(self, session_id: str, websocket: WebSocket):
        await websocket.accept()

        if session_id not in self.active_sessions:
            self.active_sessions[session_id] = []

            # Start pub/sub listener for the new session on this instance
            pubsub = self.redis.pubsub()
            await pubsub.subscribe(f"session:{session_id}")
            task = asyncio.create_task(self._listen_to_redis(session_id, pubsub))
            self.pubsub_tasks[session_id] = task
            logger.info("subscribed_to_session_channel", session_id=session_id)

        self.active_sessions[session_id].append(websocket)
        logger.info(
            "websocket_connected",
            session_id=session_id,
            active_connections=len(self.active_sessions[session_id]),
        )

    async def disconnect(self, session_id: str, websocket: WebSocket):
        if session_id in self.active_sessions:
            if websocket in self.active_sessions[session_id]:
                self.active_sessions[session_id].remove(websocket)
                logger.info(
                    "websocket_disconnected",
                    session_id=session_id,
                    remaining_connections=len(self.active_sessions[session_id]),
                )

            if not self.active_sessions[session_id]:
                del self.active_sessions[session_id]
                if session_id in self.pubsub_tasks:
                    task = self.pubsub_tasks.pop(session_id)
                    task.cancel()
                logger.info("unsubscribed_from_session_channel", session_id=session_id)

    async def broadcast(self, session_id: str, message: dict):
        """
        Pushes a message to Redis Pub/Sub, which routes it across all instances.
        The local listener will catch it and forward to all attached WebSockets.
        """
        payload = json.dumps(message)
        await self.redis.publish(f"session:{session_id}", payload)

    async def _listen_to_redis(self, session_id: str, pubsub: redis.client.PubSub):
        """
        Continuously listens for messages on the Redis Pub/Sub channel and
        broadcasts them to all locally connected websockets for this session.
        """
        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    data = message["data"]
                    websockets = self.active_sessions.get(session_id, [])
                    for ws in websockets:
                        # Forward the exact JSON string to the connected client
                        await ws.send_text(data)
        except asyncio.CancelledError:
            await pubsub.unsubscribe(f"session:{session_id}")
            await pubsub.close()
        except Exception as e:
            logger.error(
                "redis_pubsub_listener_error", session_id=session_id, error=str(e)
            )
