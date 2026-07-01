import pytest
from uuid import uuid4
from django.urls import reverse
from rest_framework.test import APIClient
from apps.consent.models import UserConsent, ConsentAuditEntry


@pytest.mark.django_db
class TestConsentAPI:
    def setup_method(self):
        self.client = APIClient()

    def test_get_consent_authenticated_owner(self, django_user_model):
        user = django_user_model.objects.create_user(
            email="api_owner@example.com", password="password123"
        )
        self.client.force_authenticate(user=user)

        url = reverse("user-consent", kwargs={"user_id": user.id})
        response = self.client.get(url)

        assert response.status_code == 200
        assert response.data["user_id"] == str(user.id)
        assert response.data["session_transcript_retention"] == "per_session"

    def test_get_consent_unauthorized_user(self, django_user_model):
        owner = django_user_model.objects.create_user(
            email="owner@example.com", password="password123"
        )
        other_user = django_user_model.objects.create_user(
            email="attacker@example.com", password="password123"
        )

        self.client.force_authenticate(user=other_user)

        url = reverse("user-consent", kwargs={"user_id": owner.id})
        response = self.client.get(url)

        assert response.status_code == 403

    def test_put_consent_updates_field_and_audit_log(self, django_user_model):
        user = django_user_model.objects.create_user(
            email="updater@example.com", password="password123"
        )
        self.client.force_authenticate(user=user)

        url = reverse("user-consent", kwargs={"user_id": user.id})
        data = {
            "session_transcript_retention": "30_days",
            "therapist_summary_access": True,
        }

        # Pass optional session context via headers
        session_id = str(uuid4())
        response = self.client.put(url, data, headers={"X-Session-Context": session_id})

        assert response.status_code == 200
        assert response.data["session_transcript_retention"] == "30_days"
        assert response.data["therapist_summary_access"] is True

        # Verify audit logs
        audit_logs = ConsentAuditEntry.objects.filter(user_id=user.id)
        assert audit_logs.count() == 2

        # Check session context was preserved
        # Note: Depending on the backend model implementation, ensure session_context is correctly cast and stored
        for log in audit_logs:
            assert str(log.session_context) == session_id

    def test_put_consent_ignores_read_only_user_id(self, django_user_model):
        user = django_user_model.objects.create_user(
            email="readonly@example.com", password="password123"
        )
        self.client.force_authenticate(user=user)

        new_user_id = str(uuid4())
        url = reverse("user-consent", kwargs={"user_id": user.id})
        data = {"user_id": new_user_id, "session_transcript_retention": "1_year"}

        response = self.client.put(url, data)
        assert response.status_code == 200
        assert response.data["user_id"] == str(user.id)  # Should NOT have changed

        consent = UserConsent.objects.get(user_id=user.id)
        assert str(consent.user_id) == str(user.id)

    def test_unauthenticated_access_denied(self, django_user_model):
        user_id = uuid4()
        url = reverse("user-consent", kwargs={"user_id": user_id})

        response = self.client.get(url)
        # DRF returns 403 Forbidden for unauthenticated users when no custom authenticators
        # are configured that handle the specific protocol (JWT middleware handles auth at Django level).
        assert response.status_code == 403

    def test_handle_django_validation_error(self, django_user_model):
        from unittest.mock import patch
        from django.core.exceptions import ValidationError as DjangoValidationError

        user = django_user_model.objects.create_user(
            email="validation@example.com", password="password123"
        )
        self.client.force_authenticate(user=user)

        url = reverse("user-consent", kwargs={"user_id": user.id})

        with patch("apps.consent.serializers.UserConsentSerializer.save") as mock_save:
            mock_save.side_effect = DjangoValidationError(
                "Direct model validation failure"
            )
            response = self.client.put(url, {"session_transcript_retention": "30_days"})

            assert response.status_code == 400
            assert str(response.data[0]) == "Direct model validation failure"

    def test_get_consent_audit_history_ordering(self, django_user_model):
        user = django_user_model.objects.create_user(
            email="audit_history@example.com", password="password123"
        )
        self.client.force_authenticate(user=user)

        url = reverse("user-consent", kwargs={"user_id": user.id})

        # Make multiple updates
        self.client.put(url, {"session_transcript_retention": "30_days"})
        self.client.put(url, {"therapist_summary_access": True})

        audit_url = reverse("consent-audit", kwargs={"user_id": user.id})
        response = self.client.get(audit_url)

        assert response.status_code == 200
        # Results might include a default record if any field was changed during creation,
        # but the signal creates it with defaults.
        # Actually, the model save() only logs CHANGES.
        # The two PUTs should definitely create 2 audit entries.
        assert len(response.data["results"]) == 2
        # Check ordering (descending by changed_at)
        assert (
            response.data["results"][0]["changed_field"] == "therapist_summary_access"
        )
        assert (
            response.data["results"][1]["changed_field"]
            == "session_transcript_retention"
        )

    def test_put_consent_model_improvement_opt_in_required(self, django_user_model):
        user = django_user_model.objects.create_user(
            email="optin@example.com", password="password123"
        )
        self.client.force_authenticate(user=user)

        url = reverse("user-consent", kwargs={"user_id": user.id})

        # Attempt to set model_improvement_data=True WITHOUT explicit_opt_in flag
        response = self.client.put(url, {"model_improvement_data": True})
        assert response.status_code == 400
        assert "explicit_opt_in" in str(response.data["model_improvement_data"])

        # Attempt WITH explicit_opt_in flag
        response = self.client.put(
            url, {"model_improvement_data": True, "explicit_opt_in": True}
        )
        assert response.status_code == 200
        assert response.data["model_improvement_data"] is True

    def test_check_consent_utility(self, django_user_model):
        from apps.consent.utils import check_consent, ConsentDeniedError

        user = django_user_model.objects.create_user(
            email="utils_test@example.com", password="password123"
        )
        # Update existing consent record created by signal
        consent = UserConsent.objects.get(user_id=user.id)
        consent.session_transcript_retention = "indefinite"
        consent.therapist_summary_access = True
        consent.save()

        # 1. Successful check
        result = check_consent(
            user.id, required_permissions=["therapist_summary_access"]
        )
        assert result.allowed is True

        # 2. Failed check (missing permission)
        with pytest.raises(ConsentDeniedError) as excinfo:
            check_consent(user.id, required_permissions=["model_improvement_data"])
        assert "model_improvement_data" in excinfo.value.missing_permissions

    def test_check_consent_cross_partner(self, django_user_model):
        from apps.consent.utils import check_consent
        from uuid import uuid4

        rel_id = uuid4()
        user1 = django_user_model.objects.create_user(
            email="p1@example.com", password="p"
        )
        user2 = django_user_model.objects.create_user(
            email="p2@example.com", password="p"
        )

        # Update existing records created by signal
        c1 = UserConsent.objects.get(user_id=user1.id)
        c1.relationship_id = rel_id
        c1.cross_partner_insight_sharing = "named"
        c1.save()

        c2 = UserConsent.objects.get(user_id=user2.id)
        c2.relationship_id = rel_id
        c2.cross_partner_insight_sharing = "never"
        c2.save()

        # Check user 1's permission for cross-partner sharing
        result = check_consent(
            user1.id,
            relationship_id=rel_id,
            required_permissions=["cross_partner_insight_sharing"],
        )

        assert result.allowed is True  # User 1 allowed it for themselves
        assert (
            result.both_partners_consented is False
        )  # But User 2 (the partner) did not
