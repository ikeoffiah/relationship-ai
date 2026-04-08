from django.test import TestCase
from django.core.management import call_command
from apps.audit.models import AuditEvent
from apps.audit.logger import AuditLogger
from apps.audit.constants import AuditEventType
import uuid
import time
import io


class AuditLoggerTest(TestCase):
    def test_audit_logger_singleton(self):
        logger1 = AuditLogger.get_instance()
        logger2 = AuditLogger.get_instance()
        self.assertIs(logger1, logger2)

    def test_audit_log_chain_integrity(self):
        logger = AuditLogger.get_instance()
        user_id = uuid.uuid4()

        # Log multiple events
        logger.log(AuditEventType.LOGIN, user_id=user_id)
        logger.log(AuditEventType.SESSION_START, user_id=user_id)
        logger.log(AuditEventType.LOGOUT, user_id=user_id)

        # Wait for threads to finish (MVP approach for tests)
        max_wait = 5
        start_time = time.time()
        while AuditEvent.objects.count() < 3 and time.time() - start_time < max_wait:
            time.sleep(0.1)

        self.assertEqual(AuditEvent.objects.count(), 3)

        # Verify chain in DB
        # First event should have 'genesis' as prev_hash
        # Note: In tests, each test case starts with a fresh DB,
        # but AuditLogger is a singleton and might have cached state if not careful.
        # However, the DB is cleared, so _get_last_hash will return 'genesis'.

        # We need to group by event_type because the chain is per event_type in the logger
        # Wait, the logger spec says: "Returns the hash of the last event of this type"
        # So LOGIN, SESSION_START, LOGOUT are different chains.

        for etype in [
            AuditEventType.LOGIN,
            AuditEventType.SESSION_START,
            AuditEventType.LOGOUT,
        ]:
            event = AuditEvent.objects.get(event_type=etype)
            self.assertEqual(event.prev_hash, "genesis")
            self.assertIsNotNone(event.hash)

    def test_verify_audit_chain_command(self):
        logger = AuditLogger.get_instance()
        user_id = uuid.uuid4()

        # Log multiple events of same type to test chain
        logger.log(AuditEventType.MEMORY_CREATED, user_id=user_id)
        logger.log(AuditEventType.MEMORY_CREATED, user_id=user_id)

        # Wait for threads
        time.sleep(1)

        # Run management command
        out = io.StringIO()
        call_command("verify_audit_chain", stdout=out)
        self.assertIn("Audit chain verified", out.getvalue())

    def test_tamper_detection(self):
        logger = AuditLogger.get_instance()
        user_id = uuid.uuid4()

        logger.log(AuditEventType.SESSION_START, user_id=user_id)
        time.sleep(0.5)

        event = AuditEvent.objects.first()
        # Tamper with the event
        event.metadata = {"tampered": True}
        event.save()

        # Verification should fail
        # Note: verify_audit_chain currently checks hash vs (prev_hash + id + timestamp)
        # It DOES NOT check metadata if it's not part of the hash.
        # Let's check the logger implementation...
        # hash_value = hashlib.sha256(f"{prev_hash}{event_id}{timestamp}".encode()).hexdigest()
        # Metadata is NOT part of the hash in the spec!
        # This is a bit weak for tamper-evidence if metadata can be changed.
        # However, I should follow the spec provided in Linear.

        # Let's tamper with the hash itself or the prev_hash
        event.hash = "invalid_hash"
        event.save()

        out = io.StringIO()
        err = io.StringIO()
        with self.assertRaises(SystemExit):
            call_command("verify_audit_chain", stdout=out, stderr=err)
        self.assertIn("AUDIT CHAIN INTEGRITY FAILURE", err.getvalue())
