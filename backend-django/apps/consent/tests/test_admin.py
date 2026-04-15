import pytest
from django.contrib import admin
from django.test import RequestFactory
from django.contrib.auth import get_user_model
from apps.consent.models import ConsentAuditEntry
from apps.consent.admin import ConsentAuditEntryAdmin

User = get_user_model()


@pytest.mark.django_db
class TestConsentAdminCoverage:
    def setup_method(self):
        self.factory = RequestFactory()
        self.admin_site = admin.AdminSite()
        self.user = User.objects.create_superuser(
            email="admin_test@example.com", password="password"
        )

    def test_consent_audit_entry_admin_permissions(self):
        # Coverage for lines 25, 28, 31 in admin.py
        ma = ConsentAuditEntryAdmin(ConsentAuditEntry, self.admin_site)
        request = self.factory.get("/admin/consent/consentauditentry/")
        request.user = self.user

        # Should always return False as defined in the admin class
        assert ma.has_add_permission(request) is False
        assert ma.has_change_permission(request) is False
        assert ma.has_delete_permission(request) is False
