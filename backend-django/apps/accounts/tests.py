from django.test import TestCase, override_settings, RequestFactory
from django.contrib.auth import get_user_model, login, authenticate
from apps.audit.models import AuditEvent
from apps.audit.constants import AuditEventType
from django.contrib.sessions.middleware import SessionMiddleware

User = get_user_model()


@override_settings(AUDIT_LOG_SYNCHRONOUS=True)
class UserSignalTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.password = "password123"
        self.user = User.objects.create_user(
            username="testuser", email="test@example.com", password=self.password
        )
        AuditEvent.objects.all().delete()

    def _get_request(self):
        request = self.factory.get("/")
        # Add session support for login()
        middleware = SessionMiddleware(lambda r: None)
        middleware.process_request(request)
        request.session.save()
        return request

    def test_login_signal_audited(self):
        request = self._get_request()
        login(request, self.user)
        self.assertTrue(
            AuditEvent.objects.filter(event_type=AuditEventType.LOGIN).exists()
        )

    def test_logout_signal_audited(self):
        from django.contrib.auth.signals import user_logged_out

        request = self._get_request()
        # Manually send the signal to ensure it's hit with the user object
        user_logged_out.send(
            sender=self.user.__class__, request=request, user=self.user
        )
        self.assertTrue(
            AuditEvent.objects.filter(event_type=AuditEventType.LOGOUT).exists()
        )

    def test_failed_login_signal_audited(self):
        authenticate(
            request=None, username="test@example.com", password="wrongpassword"
        )
        self.assertTrue(
            AuditEvent.objects.filter(event_type=AuditEventType.FAILED_AUTH).exists()
        )


class UserModelTest(TestCase):
    def test_user_str(self):
        user = User.objects.create_user(
            username="testuser2", email="test2@example.com", password="password123"
        )
        self.assertEqual(str(user), f"test2@example.com ({user.id})")
