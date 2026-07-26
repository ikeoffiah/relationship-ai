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
    A user's answer to a given day's question.

    Works solo (``relationship`` is null until a partner joins) as a private
    reflection. ``response_text`` is stored encrypted per-user. When there is a
    partner, their answer is only disclosed once the caller has answered the
    same ``date_key`` — enforced in the view/service layer, not the model.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    relationship = models.ForeignKey(
        Relationship,
        on_delete=models.CASCADE,
        related_name="daily_responses",
        null=True,
        blank=True,
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
            # A user answers once per day whether solo or coupled (a user has at
            # most one active relationship), so key uniqueness on the user.
            models.UniqueConstraint(
                fields=["user", "date_key"],
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
        Relationship,
        on_delete=models.CASCADE,
        related_name="check_ins",
        null=True,
        blank=True,
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
                fields=["user", "date_key"],
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
        Relationship,
        on_delete=models.CASCADE,
        related_name="shared_goals",
        null=True,
        blank=True,
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
        Relationship,
        on_delete=models.CASCADE,
        related_name="gratitude_moments",
        null=True,
        blank=True,
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
        if self.kind != "repair" or self.relationship_id is None:
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
        ("game_completed", "Completed a couple game"),
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
    A user's consecutive-day activity streak. A day counts if the user did any
    daily activity. Per-user (not per-couple) so it works solo and each partner
    keeps their own streak once linked — encouraging both to show up without one
    partner's off-day resetting the other's.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
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


# ── Couple games (Know Your Partner and friends) ────────────────────────


class GamePack(models.Model):
    """
    A playable pack of questions. All games share this one engine — the
    ``game_type`` decides the mechanic (guess your partner, rapid preferences,
    etc.) and ``category`` themes the content (relationship, spiritual,
    financial, spicy…). Adding a game is mostly adding a pack + questions.
    """

    GAME_TYPES = [
        ("know_your_partner", "Know Your Partner"),  # answer + guess partner, scored
        ("this_or_that", "This or That"),            # rapid preferences, compared
        ("would_you_rather", "Would You Rather"),    # answer + predict partner
        ("two_truths", "Two Truths & a Lie"),        # spot the lie
        ("conversation_deck", "Conversation Deck"),  # open prompts, no scoring
    ]
    CATEGORY_CHOICES = [
        ("relationship", "Relationship"),
        ("fun", "Fun & Quirky"),
        ("spiritual", "Faith & Values"),
        ("financial", "Money & Future"),
        ("spicy", "Spicy"),  # age-gated + per-couple opt-in, enforced in the API
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    key = models.SlugField(max_length=60, unique=True)
    title = models.CharField(max_length=120)
    description = models.CharField(max_length=280, blank=True, default="")
    game_type = models.CharField(max_length=30, choices=GAME_TYPES, default="know_your_partner")
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default="relationship")
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "game_packs"
        ordering = ["order", "created_at"]

    def __str__(self) -> str:
        return f"{self.title} ({self.game_type})"

    @property
    def is_scored(self) -> bool:
        """Guessing games score; the conversation deck is just prompts."""
        return self.game_type != "conversation_deck"

    @property
    def is_restricted(self) -> bool:
        """Spicy packs require age verification and a per-couple opt-in."""
        return self.category == "spicy"


class GameQuestion(models.Model):
    """One multiple-choice prompt in a pack. ``options`` is a list of strings;
    a guessing game scores a match between a partner's guess and the other's
    self-answer, so options must be discrete (not free text)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    pack = models.ForeignKey(GamePack, on_delete=models.CASCADE, related_name="questions")
    prompt = models.TextField()
    options = models.JSONField(default=list)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "game_questions"
        ordering = ["order"]

    def __str__(self) -> str:
        return self.prompt[:50]


class GamePlay(models.Model):
    """
    One user's answer to one game question: what is true about them
    (``self_answer``) and — in a guessing game — what they think their partner
    picked (``guess_answer``). Answers are indices into
    ``GameQuestion.options``.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    relationship = models.ForeignKey(
        Relationship, on_delete=models.CASCADE, related_name="game_plays"
    )
    pack = models.ForeignKey(GamePack, on_delete=models.CASCADE, related_name="plays")
    question = models.ForeignKey(GameQuestion, on_delete=models.CASCADE, related_name="plays")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="game_plays"
    )
    self_answer = models.PositiveSmallIntegerField(null=True, blank=True)
    guess_answer = models.PositiveSmallIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "game_plays"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "question"], name="uniq_game_play_per_user_question"
            )
        ]


class GameConsent(models.Model):
    """
    Per-user opt-in to spicy game packs, scoped to a relationship.

    Spicy packs are shown only when BOTH partners are age-verified AND both have
    opted in — a symmetric, consensual gate rather than one partner enabling
    adult content for the other.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    relationship = models.ForeignKey(
        Relationship, on_delete=models.CASCADE, related_name="game_consents"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="game_consents"
    )
    spicy_opt_in = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "game_consents"
        constraints = [
            models.UniqueConstraint(
                fields=["relationship", "user"], name="uniq_game_consent_per_user"
            )
        ]


# ── Faith & spirituality (opt-in) ───────────────────────────────────────
#
# A gentle daily practice for couples who want a shared spiritual rhythm. It is
# strictly opt-in — surfaced only when a user has expressed religious/spiritual
# values in their personalization profile — and mirrors the safety rule the
# counseling side already follows: never use faith framing to pressure someone
# to stay in an unsafe relationship (see apps/personalization/tasks.py).
#
# Content is tradition-tagged and chosen deterministically per day, exactly like
# the daily question, so both partners share the same reading with no scheduler.
# The seeded catalog uses only universal, non-sectarian reflections plus
# public-domain (KJV) scripture; richer, curated per-tradition content is a
# follow-up left to content ops, not code.


class DailyReading(models.Model):
    """
    Catalog of daily faith readings. One is surfaced per day for a given
    tradition, chosen by date ordinal (see ``services.todays_reading``).
    """

    TRADITION_CHOICES = [
        ("universal", "Universal / spiritual"),
        ("christian", "Christian"),
        ("islamic", "Islamic"),
        ("jewish", "Jewish"),
        ("buddhist", "Buddhist"),
        ("hindu", "Hindu"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tradition = models.CharField(
        max_length=20, choices=TRADITION_CHOICES, default="universal", db_index=True
    )
    title = models.CharField(max_length=200)
    reference = models.CharField(max_length=120, blank=True)  # e.g. "Psalm 133:1 (KJV)"
    body = models.TextField()  # the reading itself (public-domain / universal only)
    reflection_prompt = models.TextField()  # a question for the couple to discuss
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "daily_readings"
        ordering = ["order", "created_at"]

    def __str__(self) -> str:
        return f"[{self.tradition}] {self.title}"


class FaithPractice(models.Model):
    """
    Catalog entry for a daily spiritual practice a couple can check off
    (e.g. prayer, scripture, fasting, gratitude, an act of service). A blank
    ``tradition`` means it is shown to everyone.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    key = models.SlugField(max_length=60, unique=True)
    label = models.CharField(max_length=120)
    icon = models.CharField(max_length=8, blank=True)  # a single emoji
    tradition = models.CharField(max_length=20, blank=True, db_index=True)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "faith_practices"
        ordering = ["order", "created_at"]

    def __str__(self) -> str:
        return self.label


class FaithPracticeLog(models.Model):
    """One user's completion of a single practice on a given day."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="faith_practice_logs"
    )
    relationship = models.ForeignKey(
        Relationship,
        on_delete=models.CASCADE,
        related_name="faith_practice_logs",
        null=True,
        blank=True,
    )
    practice = models.ForeignKey(
        FaithPractice, on_delete=models.CASCADE, related_name="logs"
    )
    date_key = models.CharField(max_length=10)  # 'YYYY-MM-DD'
    completed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "faith_practice_logs"
        ordering = ["-completed_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "practice", "date_key"],
                name="uniq_faith_practice_per_day",
            )
        ]


class FaithReflection(models.Model):
    """
    A user's private, encrypted reflection on the day's reading. Encrypted at
    rest per-user exactly like ``GratitudeMoment`` — the partner never sees the
    text; it exists to make the reading a moment of pause, not a shared feed.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="faith_reflections"
    )
    relationship = models.ForeignKey(
        Relationship,
        on_delete=models.CASCADE,
        related_name="faith_reflections",
        null=True,
        blank=True,
    )
    reading = models.ForeignKey(
        DailyReading, on_delete=models.SET_NULL, related_name="reflections", null=True
    )
    date_key = models.CharField(max_length=10)
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "faith_reflections"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "date_key"], name="uniq_faith_reflection_per_day"
            )
        ]

    def save(self, *args, **kwargs):
        if self.text and not self.text.startswith("ENC:"):
            self.text = encrypt_field_value(self.user, self.text)
        super().save(*args, **kwargs)

    @property
    def decrypted_text(self) -> str:
        return decrypt_field_value(self.user, self.text)


# ── Bliss: the taggable in-chat assistant ───────────────────────────────
#
# Partners tag "@bliss" in chat to set something up — a reminder ("@bliss remind
# us to book the anniversary dinner on Friday") or a shared calendar event. The
# free text is turned into a structured draft by a deterministic parser
# (services.parse_bliss_command) that the client confirms before saving.
#
# Unlike the private, per-user encrypted content elsewhere in this app, a Bliss
# item is SHARED by design — both partners see and act on it — so its title is
# stored in plaintext, exactly like a SharedGoal title. It carries no free-form
# journalling, only a short actionable title.


class BlissItem(models.Model):
    """A reminder or calendar event created via the @bliss assistant."""

    KIND_CHOICES = [
        ("reminder", "Reminder"),
        ("event", "Calendar event"),
    ]
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("done", "Done"),
        ("cancelled", "Cancelled"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    relationship = models.ForeignKey(
        Relationship,
        on_delete=models.CASCADE,
        related_name="bliss_items",
        null=True,
        blank=True,
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="bliss_items"
    )
    kind = models.CharField(max_length=10, choices=KIND_CHOICES, default="reminder")
    title = models.CharField(max_length=200)
    # When the thing happens / the reminder should fire. May be null when the
    # parser couldn't find a time (an undated to-do).
    due_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="pending")
    # 'bliss' (parsed from a chat tag) or 'manual' (created from a form).
    source = models.CharField(max_length=10, default="bliss")
    # Set once the due-time reminder has been delivered, so the sweep never
    # fires the same reminder twice.
    reminded_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "bliss_items"
        ordering = ["due_at", "created_at"]
        indexes = [
            models.Index(fields=["relationship", "status", "due_at"]),
        ]

    def __str__(self) -> str:
        return f"[{self.kind}] {self.title}"
