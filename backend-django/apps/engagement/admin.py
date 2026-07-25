from django.contrib import admin

from apps.engagement.models import (
    DailyQuestion,
    EngagementStreak,
    GoalProgressEntry,
    GratitudeMoment,
    MicroActionTemplate,
    PointsLedger,
    SharedGoal,
)


@admin.register(DailyQuestion)
class DailyQuestionAdmin(admin.ModelAdmin):
    list_display = ("prompt_text", "category", "is_active", "order")
    list_filter = ("category", "is_active")
    search_fields = ("prompt_text",)


@admin.register(MicroActionTemplate)
class MicroActionTemplateAdmin(admin.ModelAdmin):
    list_display = ("text", "category", "target_attachment_style", "is_active")
    list_filter = ("category", "is_active", "target_attachment_style")


@admin.register(SharedGoal)
class SharedGoalAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "status", "current_value", "target_value")
    list_filter = ("category", "status", "cadence")


admin.site.register(GoalProgressEntry)
admin.site.register(GratitudeMoment)
admin.site.register(PointsLedger)
admin.site.register(EngagementStreak)
