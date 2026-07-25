"""
Daily-engagement data model.

These features exist to give couples a light, positive reason to open the app
on an ordinary day — as a counterweight to the session/relay features, which
are episodic and conflict-triggered. The design rules encoded here:

* Content the user writes (question responses, check-in notes, gratitude) is
  encrypted at rest per-user, exactly like ``apps.memory.Memory``.
* A partner's daily answer is only revealed once the caller has also answered
  (the two-sided reveal that creates the daily pull).
* Points and streaks are framed around connection, never loss-aversion, so
  nothing here punishes a missed day beyond resetting the count.
"""

import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone

from apps.relationships.models import Relationship, SharedRelationshipContext
from utils.fields import decrypt_field_value, encrypt_field_value


def today_key() -> str:
    """UTC date as a stable 'YYYY-MM-DD' bucket key for daily rollups."""
    return timezone.now().date().isoformat()


# ── Daily connection question ───────────────────────────────────────────


class DailyQuestion(models.Model):
    """
    Catalog of daily connection questions.

    Exactly one question is surfaced per day, chosen deterministically from the
    active set by the date's ordinal (see ``services.todays_question``) so no
    scheduler is required and both partners always see the same question.
    """

    CATEGORY_CHOICES = [
        ("connection", "Connection"),
        ("appreciation", "Appreciation"),
        ("growth", "Growth"),
        ("fun", "Fun"),
        ("values", "Values"),
        ("intimacy", "Intimacy"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    prompt_text = models.TextField()
    category = models.CharField(
        max_length=30, choices=CATEGORY_CHOICES, default="connection"
    )
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "daily_questions"
        ordering = ["order", "created_at"]

    def __str__(self) -> str:
        return f"[{self.category}] {self.prompt_text[:50]}"


class DailyQuestionResponse(models.Model):
    """
    One partner's answer to a given day's question.

    ``response_text`` is stored encrypted per-user. The partner's answer is only
    disclosed once the caller has answered the same ``date_key`` — enforced in
    the view/service layer, not the model.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    relationship = models.ForeignKey(
        Relationship, on_delete=models.CASCADE, related_name="daily_responses"
    )
    question = models.ForeignKey(
        DailyQuestion, on_delete=models.PROTECT, related_name="responses"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="daily_question_responses",
    )
    response_text = models.TextField()
    date_key = models.CharField(max_length=10, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "daily_question_responses"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["relationship", "user", "date_key"],
                name="uniq_daily_response_per_user_day",
            )
        ]

    def save(self, *args, **kwargs):
        if self.response_text and not self.response_text.startswith("ENC:"):
            self.response_text = encrypt_field_value(self.user, self.response_text)
        super().save(*args, **kwargs)

    @property
    def decrypted_response(self) -> str:
        return decrypt_field_value(self.user, self.response_text)


# ── Daily check-in ──────────────────────────────────────────────────────


class RelationshipCheckIn(models.Model):
    """
    A ~10-second daily pulse: how connected the user feels today (1–5), plus an
    optional mood and private note. The per-partner score series is the raw
    material for the perception-gap insight.
    """

    MOOD_CHOICES = [
        ("great", "Great"),
        ("good", "Good"),
        ("okay", "Okay"),
        ("low", "Low"),
        ("rough", "Rough"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    relationship = models.ForeignKey(
        Relationship, on_delete=models.CASCADE, related_name="check_ins"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="check_ins"
    )
    connection_score = models.PositiveSmallIntegerField()
    mood = models.CharField(max_length=10, choices=MOOD_CHOICES, blank=True, default="")
    note = models.TextField(blank=True, default="")
    date_key = models.CharField(max_length=10, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "relationship_check_ins"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["relationship", "user", "date_key"],
                name="uniq_check_in_per_user_day",
            ),
            models.CheckConstraint(
                condition=models.Q(connection_score__gte=1, connection_score__lte=5),
                name="check_in_score_1_to_5",
            ),
        ]

    def save(self, *args, **kwargs):
        if self.note and not self.note.startswith("ENC:"):
            self.note = encrypt_field_value(self.user, self.note)
        super().save(*args, **kwargs)

    @property
    def decrypted_note(self) -> str:
        return decrypt_field_value(self.user, self.note)


# ── Shared goals ────────────────────────────────────────────────────────


class SharedGoal(models.Model):
    """
    A goal a couple is working on together (fitness, savings, a habit, a trip).
    Progress is logged per day, which is the daily reason to return, and each
    log awards points shared by the couple.
    """

    CATEGORY_CHOICES = [
        ("relationship", "Relationship"),
        ("health", "Health & Fitness"),
        ("financial", "Financial"),
        ("learning", "Learning"),
        ("home", "Home & Family"),
        ("adventure", "Adventure & Travel"),
        ("custom", "Custom"),
    ]
    CADENCE_CHOICES = [
        ("daily", "Daily"),
        ("weekly", "Weekly"),
        ("once", "One-time"),
    ]
    STATUS_CHOICES = [
        ("active", "Active"),
        ("completed", "Completed"),
        ("archived", "Archived"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    relationship = models.ForeignKey(
        Relationship, on_delete=models.CASCADE, related_name="shared_goals"
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="created_goals"
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, default="")
    category = models.CharField(
        max_length=20, choices=CATEGORY_CHOICES, default="relationship"
    )
    cadence = models.CharField(max_length=10, choices=CADENCE_CHOICES, default="daily")
    target_value = models.FloatField(null=True, blank=True)
    current_value = models.FloatField(default=0.0)
    unit = models.CharField(max_length=30, blank=True, default="")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="active")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "shared_goals"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["relationship", "status"])]

    def __str__(self) -> str:
        return f"{self.title} ({self.category})"

    @property
    def progress_fraction(self) -> float:
        if not self.target_value:
            return 0.0
        return min(1.0, self.current_value / self.target_value)


class GoalProgressEntry(models.Model):
    """A single logged increment toward a shared goal, attributed to a partner."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    goal = models.ForeignKey(
        SharedGoal, on_delete=models.CASCADE, related_name="progress_entries"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="goal_progress"
    )
    value = models.FloatField(default=0.0)
    note = models.CharField(max_length=280, blank=True, default="")
    date_key = models.CharField(max_length=10, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "goal_progress_entries"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"+{self.value} on {self.goal_id}"


# ── Micro-action of the day ─────────────────────────────────────────────


class MicroActionTemplate(models.Model):
    """
    Catalog of tiny, off-app relationship actions. One is surfaced per user per
    day, matched to their attachment style when possible (blank style = any).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    text = models.TextField()
    category = models.CharField(max_length=40, blank=True, default="")
    target_attachment_style = models.CharField(max_length=50, blank=True, default="")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "micro_action_templates"
        ordering = ["created_at"]

    def __str__(self) -> str:
        return self.text[:50]


class MicroActionLog(models.Model):
    """The action assigned to a user on a given day, and whether they did it."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="micro_action_logs",
    )
    relationship = models.ForeignKey(
        Relationship,
        on_delete=models.CASCADE,
        related_name="micro_action_logs",
        null=True,
        blank=True,
    )
    template = models.ForeignKey(
        MicroActionTemplate, on_delete=models.PROTECT, related_name="logs"
    )
    date_key = models.CharField(max_length=10, db_index=True)
    completed = models.BooleanField(default=False)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "micro_action_logs"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "date_key"], name="uniq_micro_action_per_user_day"
            )
        ]


# ── Gratitude / repair quick-capture ────────────────────────────────────


class GratitudeMoment(models.Model):
    """
    A 5-second capture of something good or a repair after conflict. Repairs are
    additionally mirrored into ``SharedRelationshipContext.repair_history`` so
    the counseling side of the product can see them.
    """

    KIND_CHOICES = [
        ("gratitude", "Gratitude"),
        ("repair", "Repair"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    relationship = models.ForeignKey(
        Relationship, on_delete=models.CASCADE, related_name="gratitude_moments"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="gratitude_moments",
    )
    kind = models.CharField(max_length=10, choices=KIND_CHOICES, default="gratitude")
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "gratitude_moments"
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if self.text and not self.text.startswith("ENC:"):
            self.text = encrypt_field_value(self.user, self.text)
        super().save(*args, **kwargs)

    @property
    def decrypted_text(self) -> str:
        return decrypt_field_value(self.user, self.text)

    def mirror_repair_to_shared_context(self, plaintext: str) -> None:
        """Append a repair marker to the couple's shared context (plaintext-free)."""
        if self.kind != "repair":
            return
        ctx, _ = SharedRelationshipContext.objects.get_or_create(
            relationship=self.relationship
        )
        history = list(ctx.repair_history or [])
        history.append(
            {
                "at": self.created_at.isoformat() if self.created_at else today_key(),
                "by": str(self.user_id),
                "note_preview": plaintext[:80],
            }
        )
        ctx.repair_history = history
        ctx.save(update_fields=["repair_history"])


# ── Points & streaks (connection-framed, never punitive) ────────────────


class PointsLedger(models.Model):
    """
    Append-only record of points a partner earned, mirroring the audit-log style
    used elsewhere. Balance is the sum of a user's rows; nothing is ever debited.
    """

    REASON_CHOICES = [
        ("daily_question", "Answered daily question"),
        ("check_in", "Daily check-in"),
        ("goal_progress", "Logged goal progress"),
        ("micro_action", "Completed micro-action"),
        ("gratitude", "Shared gratitude"),
        ("repair", "Logged a repair"),
        ("both_answered_bonus", "Both partners answered"),
        ("streak_bonus", "Streak milestone"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="points_entries"
    )
    relationship = models.ForeignKey(
        Relationship,
        on_delete=models.CASCADE,
        related_name="points_entries",
        null=True,
        blank=True,
    )
    points = models.PositiveIntegerField()
    reason = models.CharField(max_length=30, choices=REASON_CHOICES)
    date_key = models.CharField(max_length=10, db_index=True)
    ref_id = models.UUIDField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "points_ledger"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "-created_at"])]

    def __str__(self) -> str:
        return f"+{self.points} {self.reason} → {self.user_id}"


class EngagementStreak(models.Model):
    """
    A couple's consecutive-day activity streak. A day counts if either partner
    did any daily activity, so the streak encourages showing up without punishing
    the couple when one partner is busy.
    """

    relationship = models.OneToOneField(
        Relationship,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name="engagement_streak",
    )
    current_streak = models.PositiveIntegerField(default=0)
    longest_streak = models.PositiveIntegerField(default=0)
    last_activity_date = models.CharField(max_length=10, blank=True, default="")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "engagement_streaks"

    def __str__(self) -> str:
        return f"Streak {self.current_streak} (best {self.longest_streak})"
