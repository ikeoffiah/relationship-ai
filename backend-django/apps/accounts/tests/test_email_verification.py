"""Verifying the address on an account, and the gate on changing it.

The rule under test is an ordering rule — verify first, change only until
verified — so most of these are about what is refused and when.
"""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient, APITestCase

from apps.accounts.models import EmailVerification

User = get_user_model()


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class EmailVerificationTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="ev@t.local", password="pw12345!")
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        mail.outbox = []

    # helpers
    def send(self):
        return self.client.post(reverse("email-send"))

    def confirm(self, code):
        return self.client.post(reverse("email-confirm"), {"code": code}, format="json")

    def change(self, email):
        return self.client.post(reverse("email-change"), {"email": email}, format="json")

    def code_from_email(self):
        body = mail.outbox[-1].body
        return "".join(c for c in body.split("code is ")[1][:6])

    def age_out_cooldown(self):
        """Move the latest record's created_at back past the resend cooldown."""
        record = EmailVerification.objects.filter(user=self.user).first()
        EmailVerification.objects.filter(pk=record.pk).update(
            created_at=timezone.now() - EmailVerification.RESEND_COOLDOWN * 2
        )

    # ── Status ───────────────────────────────────────────────────────────

    def test_a_new_account_is_unverified_and_changeable(self):
        body = self.client.get(reverse("email-status")).json()
        self.assertFalse(body["verified"])
        self.assertTrue(body["can_change"])
        self.assertEqual(body["email"], "ev@t.local")

    def test_can_change_is_answered_by_the_server_not_inferred(self):
        """The rule lives in the change endpoint, so the flag has to come from
        the same place — two implementations of one rule is how a UI ends up
        offering a button the API refuses."""
        self.user.email_verified = True
        self.user.save()
        self.assertFalse(self.client.get(reverse("email-status")).json()["can_change"])

    # ── Sending ──────────────────────────────────────────────────────────

    def test_sending_emails_a_six_digit_code(self):
        response = self.send()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["ev@t.local"])
        self.assertTrue(self.code_from_email().isdigit())
        self.assertEqual(len(self.code_from_email()), 6)

    def test_the_code_is_not_stored_in_the_clear(self):
        self.send()
        record = EmailVerification.objects.get(user=self.user)
        self.assertNotIn(self.code_from_email(), record.code_hash)
        self.assertEqual(len(record.code_hash), 64)

    def test_asking_twice_immediately_is_refused(self):
        """Otherwise the endpoint mailbombs an address the caller may not own."""
        self.send()
        second = self.send()
        self.assertEqual(second.status_code, 429)
        self.assertEqual(len(mail.outbox), 1)

    def test_a_new_code_supersedes_the_old_one(self):
        self.send()
        first_code = self.code_from_email()
        self.age_out_cooldown()
        self.send()

        # The old code must stop working the moment a new one is issued.
        self.assertEqual(self.confirm(first_code).status_code, 400)

    def test_an_already_verified_account_cannot_request_a_code(self):
        self.user.email_verified = True
        self.user.save()
        self.assertEqual(self.send().status_code, 409)

    # ── Confirming ───────────────────────────────────────────────────────

    def test_the_right_code_verifies(self):
        self.send()
        response = self.confirm(self.code_from_email())
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["verified"])
        self.user.refresh_from_db()
        self.assertTrue(self.user.email_verified)
        self.assertIsNotNone(self.user.email_verified_at)

    def test_a_wrong_code_does_not_verify_and_costs_an_attempt(self):
        self.send()
        response = self.confirm("000000")
        self.assertEqual(response.status_code, 400)
        self.user.refresh_from_db()
        self.assertFalse(self.user.email_verified)
        self.assertEqual(EmailVerification.objects.get(user=self.user).attempts, 1)

    def test_guessing_runs_out(self):
        self.send()
        for _ in range(EmailVerification.MAX_ATTEMPTS):
            self.confirm("000000")
        # Even the correct code is refused once the attempts are spent.
        self.assertEqual(self.confirm(self.code_from_email()).status_code, 400)
        self.user.refresh_from_db()
        self.assertFalse(self.user.email_verified)

    def test_an_expired_code_is_refused(self):
        self.send()
        EmailVerification.objects.filter(user=self.user).update(
            expires_at=timezone.now() - timedelta(minutes=1)
        )
        self.assertEqual(self.confirm(self.code_from_email()).status_code, 400)

    def test_a_code_cannot_be_reused(self):
        self.send()
        code = self.code_from_email()
        self.confirm(code)
        self.user.email_verified = False
        self.user.save()
        self.assertEqual(self.confirm(code).status_code, 400)

    def test_a_code_sent_to_the_old_address_cannot_verify_a_new_one(self):
        """Someone can change their address while a code is outstanding. If the
        old code still worked, verification would attest to an address nobody
        proved they could read."""
        self.send()
        code = self.code_from_email()
        self.change("moved@t.local")
        response = self.confirm(code)
        self.assertEqual(response.status_code, 400)
        self.user.refresh_from_db()
        self.assertFalse(self.user.email_verified)

    # ── Changing ─────────────────────────────────────────────────────────

    def test_changing_while_unverified_is_allowed(self):
        """The likeliest reason someone cannot verify is that they typed it
        wrong, so this has to stay open."""
        response = self.change("corrected@t.local")
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "corrected@t.local")

    def test_changing_after_verifying_is_refused(self):
        """The rule the whole feature exists for. This address is what a partner
        invitation went to; letting it move afterwards turns a verified account
        into an unverified one with nothing looking different."""
        self.send()
        self.confirm(self.code_from_email())
        response = self.change("elsewhere@t.local")
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["code"], "email_locked")
        self.user.refresh_from_db()
        self.assertEqual(self.user.email, "ev@t.local")

    def test_a_taken_address_is_refused_without_confirming_it_is_taken(self):
        """Same wording either way. A distinct "already registered" reply lets
        anyone with an account enumerate who else has one."""
        User.objects.create_user(email="taken@t.local", password="pw12345!")
        response = self.change("taken@t.local")
        self.assertEqual(response.status_code, 400)
        self.assertNotIn("registered", response.json()["message"].lower())
        self.assertNotIn("exists", response.json()["message"].lower())

    def test_a_malformed_address_is_refused(self):
        self.assertEqual(self.change("not-an-email").status_code, 400)

    def test_changing_clears_any_outstanding_code(self):
        self.send()
        self.change("moved@t.local")
        self.assertFalse(
            EmailVerification.objects.filter(
                user=self.user, used_at__isnull=True
            ).exists()
        )

    def test_all_of_it_requires_authentication(self):
        anon = APIClient()
        for name in ("email-status", "email-send", "email-confirm", "email-change"):
            response = (
                anon.get(reverse(name))
                if name == "email-status"
                else anon.post(reverse(name))
            )
            self.assertIn(response.status_code, (401, 403), name)


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class ChangePasswordTests(APITestCase):
    """Changing a password from inside the app.

    Settings used to fire a reset email and toast "a password reset email will
    be sent" — the wrong flow for somebody already signed in, and one that lets
    anyone holding an unlocked phone send mail to the owner's address.
    """

    def setUp(self):
        self.user = User.objects.create_user(email="pw@t.local", password="Curr3nt!pass")
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.url = reverse("change-password")

    def post(self, current, new):
        return self.client.post(
            self.url,
            {"current_password": current, "new_password": new},
            format="json",
        )

    def test_the_right_current_password_changes_it(self):
        response = self.post("Curr3nt!pass", "Br4ndNew!pass")
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("Br4ndNew!pass"))

    def test_a_wrong_current_password_is_refused(self):
        """The substance of the feature. A signed-in session only proves someone
        has the phone; the current password is what proves they are the account
        holder."""
        response = self.post("not-my-password", "Br4ndNew!pass")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "current_password_incorrect")
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("Curr3nt!pass"))

    def test_reusing_the_same_password_is_refused(self):
        response = self.post("Curr3nt!pass", "Curr3nt!pass")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "password_unchanged")

    def test_a_weak_new_password_is_refused_by_django_validators(self):
        """Reusing the configured validators rather than inventing a rule here
        keeps this consistent with signup and with the reset flow."""
        response = self.post("Curr3nt!pass", "123")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "password_rejected")

    def test_missing_fields_are_refused(self):
        self.assertEqual(
            self.client.post(self.url, {}, format="json").status_code, 400
        )

    def test_other_sessions_are_signed_out(self):
        """A password change is what someone does when they think another person
        has access. Leaving that person's refresh token alive would make the
        change cosmetic."""
        from apps.accounts.models import RefreshToken

        token = RefreshToken.objects.create(
            user=self.user,
            hashed_token="x" * 64,
            expires_at=timezone.now() + timedelta(days=30),
        )
        self.post("Curr3nt!pass", "Br4ndNew!pass")
        token.refresh_from_db()
        self.assertIsNotNone(token.used_at)

    def test_a_failed_attempt_is_audited(self):
        from apps.audit.models import AuditEvent

        self.post("wrong", "Br4ndNew!pass")
        self.assertTrue(
            AuditEvent.objects.filter(event_type="failed_auth").exists()
        )

    def test_it_requires_authentication(self):
        anon = APIClient()
        self.assertIn(anon.post(self.url).status_code, (401, 403))
