import csv
from django.contrib import admin
from django.http import HttpResponse
from django.utils.html import format_html
from apps.safety.models import SafetySignal, SafetyIncident


@admin.register(SafetySignal)
class SafetySignalAdmin(admin.ModelAdmin):
    list_display = ['category', 'phrase_preview', 'severity', 'source', 'created_at']
    list_filter = ['category', 'severity']
    search_fields = ['phrase', 'category']

    def phrase_preview(self, obj):
        return obj.phrase[:60] + '...' if len(obj.phrase) > 60 else obj.phrase
    phrase_preview.short_description = 'Phrase'


class TherapistNoteInline(admin.TabularInline):
    model = SafetyIncident
    fields = ['therapist_notes', 'reviewed_by', 'status']
    extra = 0
    can_delete = False


def export_incidents_as_csv(modeladmin, request, queryset):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="safety_incidents.csv"'
    writer = csv.writer(response)
    writer.writerow(['id', 'user_id_anon', 'severity', 'category', 'safety_score',
                     'layer_detected', 'action_taken', 'status', 'created_at'])
    for obj in queryset:
        writer.writerow([
            str(obj.id), obj.user_id_anon, obj.severity, obj.category,
            obj.safety_score, obj.layer_detected, obj.action_taken,
            obj.status, obj.created_at.isoformat(),
        ])
    return response

export_incidents_as_csv.short_description = 'Export selected incidents as CSV'


@admin.register(SafetyIncident)
class SafetyIncidentAdmin(admin.ModelAdmin):
    list_display = [
        'user_id_anon', 'severity_badge', 'category', 'safety_score',
        'layer_detected', 'status', 'created_at',
    ]
    list_filter = ['severity', 'category', 'status', 'layer_detected']
    search_fields = ['user_id_anon', 'session_id', 'category']
    readonly_fields = ['id', 'user_id_anon', 'session_id', 'safety_score',
                       'layer_detected', 'category', 'created_at']
    actions = [export_incidents_as_csv]
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Incident Details', {
            'fields': ('id', 'user_id_anon', 'session_id', 'severity', 'category',
                       'safety_score', 'layer_detected', 'action_taken', 'created_at'),
        }),
        ('Clinical Review', {
            'fields': ('therapist_notes', 'reviewed_by', 'status'),
        }),
    )

    def severity_badge(self, obj):
        colors = {
            'low': '#28a745', 'medium': '#ffc107',
            'high': '#fd7e14', 'critical': '#dc3545',
        }
        color = colors.get(obj.severity, '#6c757d')
        return format_html(
            '<span style="color: white; background: {}; padding: 2px 8px; '
            'border-radius: 4px; font-size: 11px;">{}</span>',
            color, obj.severity.upper()
        )
    severity_badge.short_description = 'Severity'
    severity_badge.admin_order_field = 'severity'
