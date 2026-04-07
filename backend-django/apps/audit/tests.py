from django.test import TestCase
from apps.audit.models import AuditEvent
import uuid


class AuditEventModelTest(TestCase):
    def test_audit_event_str(self):
        event = AuditEvent.objects.create(
            event_type="LOGIN_SUCCESS", user_id=uuid.uuid4()
        )
        self.assertEqual(str(event), f"LOGIN_SUCCESS at {event.created_at}")
