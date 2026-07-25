"""
API views for daily engagement.

Every relationship-scoped route resolves the caller's *own* active relationship
from ``request.user`` — the relationship id is never taken from the URL or body,
so there is no IDOR surface: a caller can only ever act on the couple they
belong to.
"""

from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.engagement import services
from apps.engagement.models import (
    DailyQuestionResponse,
    GoalProgressEntry,
    GratitudeMoment,
    MicroActionLog,
    RelationshipCheckIn,
    SharedGoal,
    today_key,
)
from apps.engagement.serializers import (
    AnswerQuestionSerializer,
    CheckInSerializer,
    CreateGoalSerializer,
    GratitudeSerializer,
    LogProgressSerializer,
    SharedGoalSerializer,
)
from apps.relationships.models import Relationship


# ── Relationship helpers ────────────────────────────────────────────────


def _active_relationship(user):
    return (
        Relationship.objects.filter(
            (Q(partner_a=user) | Q(partner_b=user)), status="active"
        )
        .first()
    )


def _partner_of(relationship, user):
    if relationship is None:
        return None
    return (
        relationship.partner_b
        if relationship.partner_a_id == user.id
        else relationship.partner_a
    )


def _display_name(user) -> str:
    if user is None:
        return "Your partner"
    return (user.full_name or "").strip() or user.email.split("@")[0]


def _needs_relationship():
    return Response(
        {"message": "This feature needs an active partner connection.", "code": "no_active_relationship"},
        status=status.HTTP_409_CONFLICT,
    )


# ── Daily question ──────────────────────────────────────────────────────


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def daily_question(request):
    """Today's question, whether each partner has answered, and — once both
    have — the two answers (the two-sided reveal)."""
    relationship = _active_relationship(request.user)
    question = services.todays_question()
    if question is None:
        return Response({"question": None})

    day = today_key()
    partner = _partner_of(relationship, request.user)

    mine = None
    theirs = None
    if relationship is not None:
        mine = DailyQuestionResponse.objects.filter(
            relationship=relationship, user=request.user, date_key=day
        ).first()
        if partner is not None:
            theirs = DailyQuestionResponse.objects.filter(
                relationship=relationship, user=partner, date_key=day
            ).first()

    i_answered = mine is not None
    partner_answered = theirs is not None
    revealed = i_answered and partner_answered  # reveal only when both are in

    return Response(
        {
            "question": {
                "id": str(question.id),
                "prompt_text": question.prompt_text,
                "category": question.category,
            },
            "date_key": day,
            "has_partner": partner is not None,
            "i_answered": i_answered,
            "partner_answered": partner_answered,
            "revealed": revealed,
            "my_answer": mine.decrypted_response if i_answered else None,
            "partner_answer": theirs.decrypted_response if revealed else None,
            "partner_name": _display_name(partner) if partner else None,
        }
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def answer_daily_question(request):
    relationship = _active_relationship(request.user)
    if relationship is None:
        return _needs_relationship()

    serializer = AnswerQuestionSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    question = services.todays_question()
    if question is None:
        return Response({"message": "No question available today."}, status=status.HTTP_404_NOT_FOUND)

    day = today_key()
    if DailyQuestionResponse.objects.filter(
        relationship=relationship, user=request.user, date_key=day
    ).exists():
        return Response(
            {"message": "You already answered today's question."},
            status=status.HTTP_409_CONFLICT,
        )

    response = DailyQuestionResponse.objects.create(
        relationship=relationship,
        question=question,
        user=request.user,
        response_text=serializer.validated_data["response_text"],
        date_key=day,
    )
    awarded, streak = services.record_daily_activity(
        request.user, relationship, "daily_question", ref_id=response.id, day_key=day
    )

    # Two-sided reveal: if the partner already answered, both are now revealed —
    # award the shared bonus and notify the partner their answers are ready.
    partner = _partner_of(relationship, request.user)
    partner_answered = (
        partner is not None
        and DailyQuestionResponse.objects.filter(
            relationship=relationship, user=partner, date_key=day
        ).exists()
    )
    revealed = partner_answered
    if revealed:
        services.award_points(request.user, relationship, "both_answered_bonus", day_key=day)
        services.notify_answers_ready(partner.id, _display_name(request.user))

    return Response(
        {
            "id": str(response.id),
            "revealed": revealed,
            "points_awarded": awarded,
            "current_streak": streak.current_streak if streak else 0,
        },
        status=status.HTTP_201_CREATED,
    )


# ── Daily check-in ──────────────────────────────────────────────────────


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def submit_check_in(request):
    relationship = _active_relationship(request.user)
    if relationship is None:
        return _needs_relationship()

    serializer = CheckInSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    day = today_key()
    if RelationshipCheckIn.objects.filter(
        relationship=relationship, user=request.user, date_key=day
    ).exists():
        return Response(
            {"message": "You already checked in today.", "code": "already_checked_in"},
            status=status.HTTP_409_CONFLICT,
        )

    check_in = RelationshipCheckIn.objects.create(
        relationship=relationship,
        user=request.user,
        connection_score=serializer.validated_data["connection_score"],
        mood=serializer.validated_data.get("mood", ""),
        note=serializer.validated_data.get("note", ""),
        date_key=day,
    )

    awarded, streak = services.record_daily_activity(
        request.user, relationship, "check_in", ref_id=check_in.id, day_key=day
    )

    partner = _partner_of(relationship, request.user)
    if partner is not None:
        services.notify_partner_checked_in(partner.id, _display_name(request.user))

    return Response(
        {
            "id": str(check_in.id),
            "points_awarded": awarded,
            "current_streak": streak.current_streak if streak else 0,
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def check_in_history(request):
    """The caller's own check-in series (for their trend chart)."""
    relationship = _active_relationship(request.user)
    if relationship is None:
        return _needs_relationship()

    days = min(int(request.query_params.get("days", 30)), 180)
    qs = RelationshipCheckIn.objects.filter(
        relationship=relationship, user=request.user
    ).order_by("-created_at")[:days]

    return Response(
        {
            "check_ins": [
                {
                    "date_key": c.date_key,
                    "connection_score": c.connection_score,
                    "mood": c.mood,
                    "created_at": c.created_at,
                }
                for c in qs
            ]
        }
    )


# ── Shared goals ────────────────────────────────────────────────────────


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def goals(request):
    relationship = _active_relationship(request.user)
    if relationship is None:
        return _needs_relationship()

    if request.method == "GET":
        qs = SharedGoal.objects.filter(relationship=relationship).exclude(status="archived")
        return Response({"goals": SharedGoalSerializer(qs, many=True).data})

    serializer = CreateGoalSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    goal = SharedGoal.objects.create(
        relationship=relationship,
        created_by=request.user,
        **serializer.validated_data,
    )
    return Response(SharedGoalSerializer(goal).data, status=status.HTTP_201_CREATED)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def log_goal_progress(request, goal_id):
    relationship = _active_relationship(request.user)
    if relationship is None:
        return _needs_relationship()

    # Scope the lookup to the caller's relationship — a goal id from another
    # couple simply 404s.
    goal = get_object_or_404(SharedGoal, id=goal_id, relationship=relationship)

    serializer = LogProgressSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    value = serializer.validated_data["value"]
    day = today_key()

    entry = GoalProgressEntry.objects.create(
        goal=goal,
        user=request.user,
        value=value,
        note=serializer.validated_data.get("note", ""),
        date_key=day,
    )

    goal.current_value = (goal.current_value or 0.0) + value
    fields = ["current_value", "updated_at"]
    if goal.target_value and goal.current_value >= goal.target_value and goal.status == "active":
        goal.status = "completed"
        goal.completed_at = timezone.now()
        fields += ["status", "completed_at"]
    goal.save(update_fields=fields)

    awarded, streak = services.record_daily_activity(
        request.user, relationship, "goal_progress", ref_id=entry.id, day_key=day
    )

    partner = _partner_of(relationship, request.user)
    if partner is not None:
        services.notify(
            partner.id,
            "goal_progress",
            title=f"{_display_name(request.user)} made progress 🎯",
            body=f"'{goal.title}' is now {int(goal.progress_fraction * 100)}% there."
            if goal.target_value
            else f"{_display_name(request.user)} logged progress on '{goal.title}'.",
            data={"deep_link": "/engagement/goals", "goal_id": str(goal.id)},
        )

    return Response(
        {
            "goal": SharedGoalSerializer(goal).data,
            "points_awarded": awarded,
            "current_streak": streak.current_streak if streak else 0,
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def update_goal(request, goal_id):
    relationship = _active_relationship(request.user)
    if relationship is None:
        return _needs_relationship()
    goal = get_object_or_404(SharedGoal, id=goal_id, relationship=relationship)

    new_status = request.data.get("status")
    if new_status not in {"active", "completed", "archived"}:
        return Response({"message": "Invalid status."}, status=status.HTTP_400_BAD_REQUEST)
    goal.status = new_status
    if new_status == "completed" and goal.completed_at is None:
        goal.completed_at = timezone.now()
    goal.save(update_fields=["status", "completed_at", "updated_at"])
    return Response(SharedGoalSerializer(goal).data)


# ── Micro-action of the day ─────────────────────────────────────────────


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def micro_action(request):
    template = services.todays_micro_action(request.user)
    if template is None:
        return Response({"action": None})

    day = today_key()
    log = MicroActionLog.objects.filter(user=request.user, date_key=day).first()
    return Response(
        {
            "action": {"id": str(template.id), "text": template.text, "category": template.category},
            "date_key": day,
            "completed": bool(log and log.completed),
        }
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def complete_micro_action(request):
    template = services.todays_micro_action(request.user)
    if template is None:
        return Response({"message": "No action available today."}, status=status.HTTP_404_NOT_FOUND)

    relationship = _active_relationship(request.user)
    day = today_key()
    log, created = MicroActionLog.objects.get_or_create(
        user=request.user,
        date_key=day,
        defaults={"template": template, "relationship": relationship},
    )
    if log.completed:
        return Response({"message": "Already completed today.", "completed": True})

    log.completed = True
    log.completed_at = timezone.now()
    log.save(update_fields=["completed", "completed_at"])

    awarded = services.award_points(request.user, relationship, "micro_action", ref_id=log.id, day_key=day)
    if relationship is not None:
        services.touch_streak(relationship, day_key=day)

    return Response({"completed": True, "points_awarded": awarded}, status=status.HTTP_200_OK)


# ── Gratitude / repair ──────────────────────────────────────────────────


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def gratitude(request):
    relationship = _active_relationship(request.user)
    if relationship is None:
        return _needs_relationship()

    serializer = GratitudeSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    kind = serializer.validated_data["kind"]
    text = serializer.validated_data["text"]

    moment = GratitudeMoment.objects.create(
        relationship=relationship, user=request.user, kind=kind, text=text
    )
    # Mirror repairs into the couple's shared context for the counseling side.
    moment.mirror_repair_to_shared_context(text)

    day = today_key()
    reason = "repair" if kind == "repair" else "gratitude"
    awarded, streak = services.record_daily_activity(
        request.user, relationship, reason, ref_id=moment.id, day_key=day
    )
    return Response(
        {
            "id": str(moment.id),
            "kind": kind,
            "points_awarded": awarded,
            "current_streak": streak.current_streak if streak else 0,
        },
        status=status.HTTP_201_CREATED,
    )


# ── Summary (points, streak, today's checklist) ─────────────────────────


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def summary(request):
    relationship = _active_relationship(request.user)
    day = today_key()
    streak = getattr(relationship, "engagement_streak", None) if relationship else None

    done = {"daily_question": False, "check_in": False, "micro_action": False}
    if relationship is not None:
        done["daily_question"] = DailyQuestionResponse.objects.filter(
            relationship=relationship, user=request.user, date_key=day
        ).exists()
        done["check_in"] = RelationshipCheckIn.objects.filter(
            relationship=relationship, user=request.user, date_key=day
        ).exists()
    log = MicroActionLog.objects.filter(user=request.user, date_key=day).first()
    done["micro_action"] = bool(log and log.completed)

    return Response(
        {
            "points_balance": services.points_balance(request.user),
            "current_streak": streak.current_streak if streak else 0,
            "longest_streak": streak.longest_streak if streak else 0,
            "today": done,
            "has_partner": relationship is not None,
        }
    )
