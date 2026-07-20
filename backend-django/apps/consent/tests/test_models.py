import pytest
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import InternalError, connection, transaction
from apps.consent.models import UserConsent, ConsentChangeLog


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
        assert str(consent) == f"Consent for {user.email}"

    def test_consent_update_creates_audit_log(self, django_user_model):
        user = django_user_model.objects.create_user(
            email="audit@example.com", password="pw"
        )
        consent = UserConsent.objects.get(user_id=user.id)

        # Update two fields
        consent.session_transcript_retention = "30_days"
        consent.therapist_summary_access = True
        consent.save()

        audit_logs = ConsentChangeLog.objects.filter(user=user).order_by(
            "dimension"
        )
        assert audit_logs.count() == 2

        assert audit_logs[0].dimension == "session_transcript_retention"
        assert audit_logs[0].old_value == "per_session"
        assert audit_logs[0].new_value == "30_days"

        assert audit_logs[1].dimension == "therapist_summary_access"
        assert audit_logs[1].old_value == "False"
        assert audit_logs[1].new_value == "True"

    def test_audit_log_is_immutable_at_db_level(self, django_user_model):
        user = django_user_model.objects.create_user(
            email="log@example.com", password="pw"
        )
        entry = ConsentChangeLog.objects.create(
            user=user, dimension="test", old_value="a", new_value="b"
        )

        with transaction.atomic():
            with pytest.raises(InternalError):
                with connection.cursor() as cursor:
                    cursor.execute(
                        "UPDATE consent_change_log SET new_value='x' WHERE id=%s",
                        [str(entry.id)],
                    )

        with transaction.atomic():
            with pytest.raises(InternalError):
                with connection.cursor() as cursor:
                    cursor.execute(
                        "DELETE FROM consent_change_log WHERE id=%s", [str(entry.id)]
                    )

    def test_consent_choice_values_are_enforced(self, django_user_model):
        """
        Consent dimensions only accept their declared choice values.

        NOTE: this is enforced at the model layer (Django `choices` +
        full_clean), not by a database CHECK constraint -- no CHECK constraint
        is created for these columns by apps/consent/migrations/0001_initial.py,
        so a raw UPDATE can still write an out-of-domain value.
        """
        user = django_user_model.objects.create_user(
            email="constraint@example.com", password="pw"
        )
        consent = UserConsent.objects.get(user_id=user.id)

        # An out-of-domain value is rejected by model validation...
        consent.session_transcript_retention = "invalid"
        with pytest.raises(DjangoValidationError) as excinfo:
            consent.full_clean()
        assert "session_transcript_retention" in excinfo.value.message_dict

        # ...while every declared choice is accepted.
        for value, _label in UserConsent.SESSION_RETENTION_CHOICES:
            consent.session_transcript_retention = value
            consent.full_clean()
