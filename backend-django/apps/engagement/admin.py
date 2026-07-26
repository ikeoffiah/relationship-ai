from django.contrib import admin

from apps.engagement.models import (
    GameConsent,
    DailyQuestion,
    DailyReading,
    EngagementStreak,
    FaithPractice,
    GamePack,
    GameQuestion,
    GoalProgressEntry,
    GratitudeMoment,
    MicroActionTemplate,
    PointsLedger,
    SharedGoal,
)


class GameQuestionInline(admin.TabularInline):
    model = GameQuestion
    extra = 1


@admin.register(GamePack)
class GamePackAdmin(admin.ModelAdmin):
    list_display = ("title", "key", "game_type", "category", "is_active", "order")
    list_filter = ("game_type", "category", "is_active")
    prepopulated_fields = {"key": ("title",)}
    inlines = [GameQuestionInline]


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

admin.site.register(GameConsent)


@admin.register(DailyReading)
class DailyReadingAdmin(admin.ModelAdmin):
    list_display = ("title", "tradition", "reference", "is_active", "order")
    list_filter = ("tradition", "is_active")
    search_fields = ("title", "reference")


@admin.register(FaithPractice)
class FaithPracticeAdmin(admin.ModelAdmin):
    list_display = ("label", "key", "tradition", "is_active", "order")
    list_filter = ("tradition", "is_active")
