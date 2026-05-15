from django.contrib import admin
from apps.consent.models import UserConsent, ConsentChangeLog


@admin.register(UserConsent)
class UserConsentAdmin(admin.ModelAdmin):
    list_display = ("user", "session_transcript_retention", "cross_partner_insight_sharing", "updated_at")
    list_filter = (
        "session_transcript_retention",
        "cross_partner_insight_sharing",
        "joint_session_participation",
        "shared_relationship_context",
    )
    search_fields = ("user__email", "user__id")
    readonly_fields = ("updated_at",)


@admin.register(ConsentChangeLog)
class ConsentChangeLogAdmin(admin.ModelAdmin):
    list_display = ("user", "dimension", "old_value", "new_value", "changed_at")
    list_filter = ("dimension",)
    search_fields = ("user__email", "user__id", "changed_from_session_id")
    readonly_fields = ("changed_at", "user", "dimension", "old_value", "new_value", "changed_from_session_id", "ip_address", "user_agent")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
