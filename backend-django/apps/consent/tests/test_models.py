import pytest
from uuid import uuid4
from django.core.exceptions import ValidationError
from django.db import InternalError, IntegrityError, connection, transaction
from apps.consent.models import UserConsent, ConsentAuditEntry


@pytest.mark.django_db(transaction=True)
class TestConsentSystem:
    def test_default_values_are_most_restrictive(self, django_user_model):
        user = django_user_model.objects.create_user(
            email="test@example.com", password="pw"
        )
        # Verify auto-creation via signal
        consent = UserConsent.objects.get(user_id=user.id)

        assert consent.session_transcript_retention == "per_session"
        assert consent.cross_partner_insight_sharing == "never"
        assert consent.joint_session_participation == "not_enrolled"
        assert consent.shared_relationship_context == "not_participating"
        assert consent.therapist_summary_access is False
        assert consent.model_improvement_data is False
        assert str(consent) == f"Consent for {user.id}"

    def test_consent_update_creates_audit_log(self, django_user_model):
        user = django_user_model.objects.create_user(
            email="audit@example.com", password="pw"
        )
        consent = UserConsent.objects.get(user_id=user.id)

        # Update two fields
        consent.session_transcript_retention = "30_days"
        consent.therapist_summary_access = True
        consent.updated_by = user.id
        consent.save()

        audit_logs = ConsentAuditEntry.objects.filter(user_id=user.id).order_by(
            "changed_field"
        )
        assert audit_logs.count() == 2

        assert audit_logs[0].changed_field == "session_transcript_retention"
        assert audit_logs[0].old_value == "per_session"
        assert audit_logs[0].new_value == "30_days"

        assert audit_logs[1].changed_field == "therapist_summary_access"
        assert audit_logs[1].old_value == "False"
        assert audit_logs[1].new_value == "True"

    def test_user_id_is_immutable(self, django_user_model):
        user = django_user_model.objects.create_user(
            email="immutable@example.com", password="pw"
        )
        consent = UserConsent.objects.get(user_id=user.id)

        consent.user_id = uuid4()
        consent.updated_by = user.id
        with pytest.raises(ValidationError, match="user_id cannot be changed."):
            consent.save()

    def test_updated_by_must_match_user_id(self, django_user_model):
        user = django_user_model.objects.create_user(
            email="owner@example.com", password="pw"
        )
        consent = UserConsent.objects.get(user_id=user.id)

        consent.therapist_summary_access = True
        consent.updated_by = uuid4()
        with pytest.raises(
            ValidationError,
            match="Consent can only be updated by the record's own user_id.",
        ):
            consent.save()

    def test_audit_log_is_immutable_at_db_level(self, django_user_model):
        user = django_user_model.objects.create_user(
            email="log@example.com", password="pw"
        )
        entry = ConsentAuditEntry.objects.create(
            user_id=user.id, changed_field="test", old_value="a", new_value="b"
        )

        with transaction.atomic():
            with pytest.raises(InternalError):
                with connection.cursor() as cursor:
                    cursor.execute(
                        "UPDATE consent_audit_log SET new_value='x' WHERE id=%s",
                        [str(entry.id)],
                    )

        with transaction.atomic():
            with pytest.raises(InternalError):
                with connection.cursor() as cursor:
                    cursor.execute(
                        "DELETE FROM consent_audit_log WHERE id=%s", [str(entry.id)]
                    )

    def test_db_check_constraints_enforcement(self, django_user_model):
        user = django_user_model.objects.create_user(
            email="constraint@example.com", password="pw"
        )
        consent = UserConsent.objects.get(user_id=user.id)

        with transaction.atomic():
            with pytest.raises(IntegrityError):
                with connection.cursor() as cursor:
                    cursor.execute(
                        "UPDATE user_consents SET session_transcript_retention='invalid' WHERE id=%s",
                        [str(consent.id)],
                    )
