"""
Shared business logic for daily engagement: deterministic daily-content
selection, the points ledger, connection-framed streaks, and notifications.

Kept out of the views so the reveal/points/streak rules live in one place and
are unit-testable without HTTP.
"""

from datetime import date, timedelta
from typing import Optional

from django.utils import timezone

from apps.engagement.models import (
    DailyQuestion,
    EngagementStreak,
    MicroActionTemplate,
    PointsLedger,
    today_key,
)
from apps.notifications.notification_models import Notification, NotificationType

# Points are deliberately small and flat — this is a warmth signal, not a
# grind. Repairs are worth the most because they are the hardest and most
# valuable relationship behaviour.
POINTS = {
    "check_in": 5,
    "daily_question": 10,
    "goal_progress": 10,
    "micro_action": 5,
    "gratitude": 5,
    "repair": 15,
    "both_answered_bonus": 10,
}


# ── Deterministic daily content ─────────────────────────────────────────


def _day_ordinal(day: Optional[date] = None) -> int:
    return (day or timezone.now().date()).toordinal()


def todays_question(day: Optional[date] = None) -> Optional[DailyQuestion]:
    """
    The one question for today, the same for both partners, chosen by rotating
    through the active catalog by date ordinal. No scheduler needed.
    """
    questions = list(DailyQuestion.objects.filter(is_active=True).order_by("order", "created_at"))
    if not questions:
        return None
    return questions[_day_ordinal(day) % len(questions)]


def todays_micro_action(user, day: Optional[date] = None) -> Optional[MicroActionTemplate]:
    """
    Today's micro-action for a user, preferring templates that match their
    attachment style and falling back to universal ones. Deterministic per
    (user, day) so it doesn't shuffle on refresh.
    """
    style = ""
    profile = getattr(user, "personalization_profile", None)
    if profile is not None:
        style = (profile.attachment_style or "").strip()

    matched = list(
        MicroActionTemplate.objects.filter(
            is_active=True, target_attachment_style=style
        ).order_by("created_at")
    ) if style else []
    pool = matched or list(
        MicroActionTemplate.objects.filter(
            is_active=True, target_attachment_style=""
        ).order_by("created_at")
    )
    pool = pool or list(MicroActionTemplate.objects.filter(is_active=True).order_by("created_at"))
    if not pool:
        return None
    # Vary by user so partners don't always get the identical action.
    seed = _day_ordinal(day) + (hash(str(getattr(user, "id", ""))) % 97)
    return pool[seed % len(pool)]


# ── Points ──────────────────────────────────────────────────────────────


def award_points(user, relationship, reason: str, ref_id=None, day_key: Optional[str] = None) -> int:
    """Record a points entry and return the amount awarded."""
    amount = POINTS.get(reason, 0)
    if amount <= 0:
        return 0
    PointsLedger.objects.create(
        user=user,
        relationship=relationship,
        points=amount,
        reason=reason,
        date_key=day_key or today_key(),
        ref_id=ref_id,
    )
    return amount


def points_balance(user) -> int:
    from django.db.models import Sum

    return PointsLedger.objects.filter(user=user).aggregate(total=Sum("points"))["total"] or 0


# ── Streaks (connection-framed) ─────────────────────────────────────────


def touch_streak(user, day_key: Optional[str] = None) -> EngagementStreak:
    """
    Register that the user did some daily activity today and roll their streak
    forward. Idempotent within a day; resets (never goes negative) if a day was
    missed. Works solo — the streak is per-user, not per-couple.
    """
    day_key = day_key or today_key()
    streak, _ = EngagementStreak.objects.get_or_create(user=user)

    if streak.last_activity_date == day_key:
        return streak  # already counted today

    yesterday = (date.fromisoformat(day_key) - timedelta(days=1)).isoformat()
    if streak.last_activity_date == yesterday:
        streak.current_streak += 1
    else:
        streak.current_streak = 1

    streak.longest_streak = max(streak.longest_streak, streak.current_streak)
    streak.last_activity_date = day_key
    streak.save()
    return streak


def record_daily_activity(user, relationship, reason: str, ref_id=None, day_key: Optional[str] = None):
    """Convenience: award points and advance the streak for one daily action.

    ``relationship`` may be ``None`` (solo user); points are still awarded and
    the per-user streak still advances.
    """
    day_key = day_key or today_key()
    awarded = award_points(user, relationship, reason, ref_id=ref_id, day_key=day_key)
    streak = touch_streak(user, day_key=day_key)
    return awarded, streak


# ── Notifications ───────────────────────────────────────────────────────


def notify(user_id, notif_type: str, title: str, body: str = "", data: Optional[dict] = None) -> Notification:
    return Notification.objects.create(
        user_id=user_id,
        type=notif_type,
        title=title,
        body=body,
        data=data or {},
    )


def notify_answers_ready(recipient_id, partner_name: str) -> Notification:
    """Real-payload push when the second partner answers the daily question."""
    return notify(
        recipient_id,
        NotificationType.DAILY_QUESTION_READY,
        title="Today's answers are ready 💬",
        body=f"{partner_name} answered today's question. Tap to see both answers.",
        data={"deep_link": "/engagement/daily-question"},
    )


def notify_partner_checked_in(recipient_id, partner_name: str) -> Notification:
    return notify(
        recipient_id,
        NotificationType.PARTNER_CHECKED_IN,
        title=f"{partner_name} checked in",
        body="See how you're both feeling today.",
        data={"deep_link": "/engagement/check-in"},
    )
