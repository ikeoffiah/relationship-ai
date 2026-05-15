import pytest
from uuid import uuid4
from apps.consent.models import UserConsent
from apps.consent.utils import check_consent, ConsentDeniedError


@pytest.mark.django_db
class TestConsentUtilsCoverage:
    def test_check_consent_no_record(self):
        # Case: user_id has no UserConsent record
        user_id = uuid4()
        result = check_consent(
            user_id, required_permissions=["therapist_summary_access"]
        )

        assert result.allowed is False
        assert "therapist_summary_access" in result.missing_permissions
        assert result.both_partners_consented is False

    def test_check_consent_choice_field_negative(self, django_user_model):
        # Case: choice field has a value that implies no consent (like 'never')
        user = django_user_model.objects.create_user(
            email="negative_choice@example.com", password="password123"
        )
        # Update existing record (created by signal)
        consent = UserConsent.objects.get(user_id=user.id)
        consent.cross_partner_insight_sharing = "never"
        consent.save()

        with pytest.raises(ConsentDeniedError) as excinfo:
            check_consent(
                user.id, required_permissions=["cross_partner_insight_sharing"]
            )

        assert "cross_partner_insight_sharing" in excinfo.value.missing_permissions

    def test_check_consent_unknown_permission(self, django_user_model):
        # Case: requesting a permission that doesn't exist on the model
        user = django_user_model.objects.create_user(
            email="unknown_perm@example.com", password="password123"
        )

        with pytest.raises(ConsentDeniedError) as excinfo:
            check_consent(user.id, required_permissions=["non_existent_field"])

        assert "non_existent_field" in excinfo.value.missing_permissions
