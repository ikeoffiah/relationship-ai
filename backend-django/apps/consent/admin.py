from django.contrib import admin
from apps.consent.models import UserConsent, ConsentAuditEntry


@admin.register(UserConsent)
class UserConsentAdmin(admin.ModelAdmin):
    list_display = ("user_id", "relationship_id", "updated_at", "updated_by")
    list_filter = (
        "session_transcript_retention",
        "cross_partner_insight_sharing",
        "joint_session_participation",
    )
    search_fields = ("user_id", "relationship_id")
    readonly_fields = ("updated_at",)


@admin.register(ConsentAuditEntry)
class ConsentAuditEntryAdmin(admin.ModelAdmin):
    list_display = ("user_id", "changed_field", "old_value", "new_value", "changed_at")
    list_filter = ("changed_field",)
    search_fields = ("user_id", "relationship_id", "session_context")
    readonly_fields = ("changed_at",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
