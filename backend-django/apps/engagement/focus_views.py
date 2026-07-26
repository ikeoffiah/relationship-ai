"""
API for consensual Focus Mode.

A Focus session is a mutual, opt-in "let's be present together" timer. It is the
healthy inverse of a controlling app-lock: it locks and monitors nothing, one
partner proposes and the other accepts, and EITHER partner can end it instantly.

* ``GET  focus``          — the couple's current (proposed/active) session, with
  remaining time.
* ``POST focus/propose``  — propose a session {duration_minutes}; notifies the
  partner. 409 if one is already live.
* ``POST focus/accept``   — the partner (not the proposer) accepts → active.
* ``POST focus/decline``  — the partner declines.
* ``POST focus/end``      — EITHER partner ends the current session at any time.

All routes resolve the caller's own active relationship from ``request.user``.
"""

from django.utils import timezone
from datetime import timedelta

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.engagement import services
from apps.engagement.models import FocusSession
from apps.engagement.views import _active_relationship, _partner_of
from apps.notifications.notification_models import NotificationType

MIN_MINUTES = 5
MAX_MINUTES = 180


def _current(relationship):
    if relationship is None:
        return None
    return FocusSession.objects.filter(
        relationship=relationship, status__in=["proposed", "active"]
    ).first()


def _serialize(session, user):
    if session is None:
        return {"session": None}
    now = timezone.now()
    remaining = None
    complete = False
    if session.status == "active" and session.ends_at:
        remaining = max(0, int((session.ends_at - now).total_seconds()))
        complete = remaining == 0
    return {
        "session": {
            "id": str(session.id),
            "status": session.status,
            "duration_minutes": session.duration_minutes,
            "i_initiated": session.initiated_by_id == user.id,
            "started_at": session.started_at.isoformat() if session.started_at else None,
            "ends_at": session.ends_at.isoformat() if session.ends_at else None,
            "remaining_seconds": remaining,
            "is_complete": complete,
        }
    }


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def current(request):
    relationship = _active_relationship(request.user)
    return Response(_serialize(_current(relationship), request.user))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def propose(request):
    relationship = _active_relationship(request.user)
    partner = _partner_of(relationship, request.user)
    if relationship is None or partner is None:
        return Response(
            {"detail": "Focus Mode is for two — invite your partner first."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    existing = _current(relationship)
    if existing is not None:
        # Don't clobber a live session; hand back the current one.
        return Response(_serialize(existing, request.user), status=status.HTTP_409_CONFLICT)

    try:
        minutes = int(request.data.get("duration_minutes", 20))
    except (TypeError, ValueError):
        return Response({"detail": "duration_minutes must be a number."}, status=status.HTTP_400_BAD_REQUEST)
    minutes = max(MIN_MINUTES, min(MAX_MINUTES, minutes))

    session = FocusSession.objects.create(
        relationship=relationship, initiated_by=request.user, duration_minutes=minutes
    )
    services.notify(
        partner.id,
        NotificationType.FOCUS_PROPOSED,
        title="Focus together? 🌿",
        body=f"{_short(request.user)} wants {minutes} minutes, phones down, just you two.",
        data={"deep_link": "/engagement/focus"},
    )
    return Response(_serialize(session, request.user), status=status.HTTP_201_CREATED)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def accept(request):
    relationship = _active_relationship(request.user)
    session = _current(relationship)
    if session is None or session.status != "proposed":
        return Response({"detail": "No focus invite to accept."}, status=status.HTTP_404_NOT_FOUND)
    if session.initiated_by_id == request.user.id:
        return Response(
            {"detail": "Wait for your partner to accept your invite."},
            status=status.HTTP_409_CONFLICT,
        )
    now = timezone.now()
    session.status = "active"
    session.started_at = now
    session.ends_at = now + timedelta(minutes=session.duration_minutes)
    session.save(update_fields=["status", "started_at", "ends_at"])

    services.notify(
        session.initiated_by_id,
        NotificationType.FOCUS_STARTED,
        title="Focus time 🌿",
        body=f"{_short(request.user)} is in. Phones down — enjoy each other.",
        data={"deep_link": "/engagement/focus"},
    )
    return Response(_serialize(session, request.user))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def decline(request):
    relationship = _active_relationship(request.user)
    session = _current(relationship)
    if session is None or session.status != "proposed":
        return Response({"detail": "No focus invite to decline."}, status=status.HTTP_404_NOT_FOUND)
    if session.initiated_by_id == request.user.id:
        return Response({"detail": "That's your own invite."}, status=status.HTTP_409_CONFLICT)
    session.status = "declined"
    session.ended_at = timezone.now()
    session.save(update_fields=["status", "ended_at"])
    services.notify(
        session.initiated_by_id,
        NotificationType.FOCUS_ENDED,
        title="Maybe later 💛",
        body=f"{_short(request.user)} isn't up for focus time right now.",
        data={"deep_link": "/engagement/focus"},
    )
    return Response(_serialize(None, request.user))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def end(request):
    """Either partner can end the current session at any moment — no permission
    needed. This is the core consent guarantee of Focus Mode."""
    relationship = _active_relationship(request.user)
    session = _current(relationship)
    if session is None:
        return Response({"detail": "No focus session to end."}, status=status.HTTP_404_NOT_FOUND)

    was_active = session.status == "active"
    session.status = "ended"
    session.ended_at = timezone.now()
    session.save(update_fields=["status", "ended_at"])

    # A completed shared focus session is a small win for both.
    if was_active:
        partner = _partner_of(relationship, request.user)
        for u in [request.user, partner]:
            if u is not None:
                services.record_daily_activity(u, relationship, "focus_completed")
        if partner is not None:
            services.notify(
                partner.id,
                NotificationType.FOCUS_ENDED,
                title="Focus time ended 🌿",
                body="Hope it was a good moment together.",
                data={"deep_link": "/engagement/focus"},
            )
    return Response(_serialize(None, request.user))


def _short(user, n: int = 24) -> str:
    name = user.full_name or user.email.split("@")[0]
    return name if len(name) <= n else name[: n - 1] + "…"
