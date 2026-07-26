"""DRF serializers for the daily-engagement API."""

from rest_framework import serializers

from apps.engagement.models import (
    GoalProgressEntry,
    SharedGoal,
)


# ── Input serializers ───────────────────────────────────────────────────


class AnswerQuestionSerializer(serializers.Serializer):
    response_text = serializers.CharField(max_length=2000, trim_whitespace=True)


class FaithReflectSerializer(serializers.Serializer):
    text = serializers.CharField(max_length=4000, trim_whitespace=True)


class CheckInSerializer(serializers.Serializer):
    connection_score = serializers.IntegerField(min_value=1, max_value=5)
    mood = serializers.ChoiceField(
        choices=["great", "good", "okay", "low", "rough"], required=False, allow_blank=True
    )
    note = serializers.CharField(max_length=1000, required=False, allow_blank=True)


class CreateGoalSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=200)
    description = serializers.CharField(max_length=2000, required=False, allow_blank=True)
    category = serializers.ChoiceField(
        choices=[c[0] for c in SharedGoal.CATEGORY_CHOICES], default="relationship"
    )
    cadence = serializers.ChoiceField(
        choices=[c[0] for c in SharedGoal.CADENCE_CHOICES], default="daily"
    )
    target_value = serializers.FloatField(required=False, allow_null=True)
    unit = serializers.CharField(max_length=30, required=False, allow_blank=True)


class LogProgressSerializer(serializers.Serializer):
    value = serializers.FloatField(default=0.0)
    note = serializers.CharField(max_length=280, required=False, allow_blank=True)


class GratitudeSerializer(serializers.Serializer):
    kind = serializers.ChoiceField(choices=["gratitude", "repair"], default="gratitude")
    text = serializers.CharField(max_length=2000, trim_whitespace=True)


# ── Output serializers ──────────────────────────────────────────────────


class GoalProgressEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = GoalProgressEntry
        fields = ["id", "user", "value", "note", "date_key", "created_at"]
        read_only_fields = fields


class SharedGoalSerializer(serializers.ModelSerializer):
    progress_fraction = serializers.FloatField(read_only=True)

    class Meta:
        model = SharedGoal
        fields = [
            "id",
            "created_by",
            "title",
            "description",
            "category",
            "cadence",
            "target_value",
            "current_value",
            "progress_fraction",
            "unit",
            "status",
            "created_at",
            "completed_at",
        ]
        read_only_fields = fields
