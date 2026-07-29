"""DRF serializers for the daily-engagement API."""

from rest_framework import serializers

from apps.engagement.models import (
    BlissItem,
    Commitment,
    GoalProgressEntry,
    SharedGoal,
)


# ── Input serializers ───────────────────────────────────────────────────


class AnswerQuestionSerializer(serializers.Serializer):
    response_text = serializers.CharField(max_length=2000, trim_whitespace=True)


class FaithReflectSerializer(serializers.Serializer):
    text = serializers.CharField(max_length=4000, trim_whitespace=True)


class BlissItemSerializer(serializers.ModelSerializer):
    created_by_me = serializers.SerializerMethodField()
    awaiting_my_answer = serializers.SerializerMethodField()

    class Meta:
        model = BlissItem
        fields = [
            "id",
            "kind",
            "title",
            "due_at",
            "status",
            "source",
            "partner_invite",
            "partner_responded_at",
            "created_by_me",
            "awaiting_my_answer",
            "created_at",
        ]
        read_only_fields = fields

    def get_created_by_me(self, obj) -> bool:
        viewer = self.context.get("viewer_id")
        return viewer is not None and obj.created_by_id == viewer

    def get_awaiting_my_answer(self, obj) -> bool:
        """Whether *this reader* is the one being asked.

        Computed server-side rather than left to the client to work out from
        partner_invite plus who created it. Getting it wrong in the other
        direction would show the person who sent the invite an Accept button
        for their own request.
        """
        viewer = self.context.get("viewer_id")
        return (
            viewer is not None
            and obj.partner_invite == BlissItem.INVITE_PENDING
            and obj.created_by_id != viewer
        )


class CreateBlissItemSerializer(serializers.Serializer):
    kind = serializers.ChoiceField(choices=["reminder", "event"], default="reminder")
    title = serializers.CharField(max_length=200, trim_whitespace=True)
    due_at = serializers.DateTimeField(required=False, allow_null=True)
    # "couple_chat" is not cosmetic: it is the only value that causes the item
    # to be announced in the couple's thread. An item created from a private
    # counseling session must never post there — that would leak the existence
    # of the session to the partner.
    source = serializers.ChoiceField(
        choices=["bliss", "manual", "couple_chat"], default="bliss"
    )
    # Tag the partner. Doing so does not put the item on their calendar as a
    # commitment — it asks them, and the reminder only reaches them if they say
    # yes.
    invite_partner = serializers.BooleanField(default=False)


class InviteResponseSerializer(serializers.Serializer):
    accept = serializers.BooleanField()


class CommitmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Commitment
        fields = ["id", "kind", "text", "remind_at", "status", "created_by", "created_at"]
        read_only_fields = fields


class CreateCommitmentSerializer(serializers.Serializer):
    kind = serializers.ChoiceField(choices=["for_partner", "with_partner"])
    text = serializers.CharField(max_length=280, trim_whitespace=True)
    remind_at = serializers.DateTimeField(required=False, allow_null=True)


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
