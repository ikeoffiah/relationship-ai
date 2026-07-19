from django.contrib import admin
from apps.config.models import SystemConfig, SystemConfigAudit

THRESHOLD_KEYS = [
    'flooding_indicator_threshold',
    'abuse_signal_threshold',
    'enrichment_signal_threshold',
    'contempt_threshold',
    'criticism_threshold',
    'defensiveness_threshold',
    'stonewalling_threshold',
]


class SystemConfigAuditInline(admin.TabularInline):
    model = SystemConfigAudit
    fields = ['old_value', 'new_value', 'changed_by', 'change_reason', 'changed_at']
    readonly_fields = ['old_value', 'new_value', 'changed_by', 'change_reason', 'changed_at']
    extra = 0
    can_delete = False
    ordering = ['-changed_at']


@admin.register(SystemConfig)
class SystemConfigAdmin(admin.ModelAdmin):
    list_display = ['key', 'value', 'description_short', 'last_changed_by', 'last_changed_at']
    search_fields = ['key', 'description']
    readonly_fields = ['last_changed_at']
    fields = ['key', 'value', 'description', 'change_reason', 'last_changed_by', 'last_changed_at']

    def description_short(self, obj):
        return obj.description[:60] + '...' if len(obj.description) > 60 else obj.description
    description_short.short_description = 'Description'

    def save_model(self, request, obj, form, change):
        if change:
            # Record what the old value was before saving
            old = SystemConfig.objects.get(pk=obj.pk)
            SystemConfigAudit.objects.create(
                config_key=obj.key,
                old_value=old.value,
                new_value=obj.value,
                changed_by=request.user,
                change_reason=obj.change_reason or '(no reason provided)',
            )
        obj.last_changed_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(SystemConfigAudit)
class SystemConfigAuditAdmin(admin.ModelAdmin):
    list_display = ['config_key', 'old_value', 'new_value', 'changed_by', 'change_reason', 'changed_at']
    list_filter = ['config_key', 'changed_at']
    readonly_fields = ['config_key', 'old_value', 'new_value', 'changed_by', 'change_reason', 'changed_at']

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
