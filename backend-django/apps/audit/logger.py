import hashlib
import json
import logging
import os
import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from django.conf import settings
from django.db import connection, transaction

logger = logging.getLogger("audit")
fallback_logger = logging.getLogger("audit.fallback")


class AuditLogger:
    """
    MVP implementation: writes audit events directly to PostgreSQL.
    Same interface as the post-pilot Kafka-based implementation.
    Non-blocking: uses a background thread to avoid adding latency to the session pipeline.
    """

    _instance = None
    _lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> "AuditLogger":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def log(
        self,
        event_type: str,
        user_id: Optional[Any] = None,
        metadata: Optional[Dict[str, Any]] = None,
        session_id: Optional[Any] = None,
        relationship_id: Optional[Any] = None,
    ) -> str:
        """
        Logs an audit event. Returns the event ID immediately.
        Writing to DB happens in a background thread.
        """
        event_id = str(uuid.uuid4())
        
        # Check if we should log synchronously (useful for tests)
        if getattr(settings, "AUDIT_LOG_SYNCHRONOUS", False):
            self._write_event(
                event_id, event_type, user_id, metadata, session_id, relationship_id
            )
            return event_id

        # Non-blocking: fire and forget via background thread
        thread = threading.Thread(
            target=self._write_event,
            args=(event_id, event_type, user_id, metadata, session_id, relationship_id),
            daemon=True,
        )
        thread.start()
        return event_id

    def _write_event(
        self,
        event_id: str,
        event_type: str,
        user_id: Optional[Any],
        metadata: Optional[Dict[str, Any]],
        session_id: Optional[Any],
        relationship_id: Optional[Any],
    ):
        timestamp = datetime.now(timezone.utc).isoformat()
        try:
            prev_hash = self._get_last_hash(event_type)
            hash_value = hashlib.sha256(
                f"{prev_hash}{event_id}{timestamp}".encode()
            ).hexdigest()

            # Ensure metadata is JSON-serializable
            metadata_json = json.dumps(metadata or {})

            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO audit_events
                        (id, event_type, user_id, relationship_id, session_id,
                         metadata, prev_hash, hash, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        [
                            event_id,
                            event_type,
                            user_id,
                            relationship_id,
                            session_id,
                            metadata_json,
                            prev_hash,
                            hash_value,
                            timestamp,
                        ],
                    )
        except Exception as e:
            # MUST NOT raise — log to local fallback file instead
            fallback_logger.error(f"Audit write failed: {event_type} {event_id}: {e}")

            # Local fallback: append to audit_fallback.log for manual recovery
            fallback_path = os.path.join(settings.BASE_DIR, "audit_fallback.log")
            try:
                with open(fallback_path, "a") as f:
                    f.write(
                        f"{timestamp} | {event_type} | {event_id} | {user_id} | {metadata}\n"
                    )
            except Exception as fallback_err:
                # If even the fallback file fails, log to system stderr
                logger.critical(f"CRITICAL: Audit fallback failed: {fallback_err}")

    def _get_last_hash(self, event_type: str) -> str:
        """Returns the hash of the last event of this type for chain linking."""
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT hash FROM audit_events
                    WHERE event_type = %s
                    ORDER BY created_at DESC LIMIT 1
                    """,
                    [event_type],
                )
                row = cursor.fetchone()
            return row[0] if row else "genesis"
        except Exception:
            # If DB query fails during hash lookup, default to genesis to allow append
            # Error will be caught in _write_event
            return "genesis"
