"""
API views for the opt-in faith / spirituality practice.

Three routes, all scoped to ``request.user`` (no IDOR surface):

* ``GET  faith/today``               — today's reading + the practice checklist
                                        with the caller's completion state.
* ``POST faith/practices/complete``  — check off one practice for today.
* ``POST faith/reflect``             — save a private reflection on the reading.

Everything is solo-friendly: the relationship is resolved from the caller when
present but is never required, so a single user keeps their own streak.
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.engagement import services
from apps.engagement.models import (
    FaithPractice,
    FaithPracticeLog,
    FaithReflection,
    today_key,
)
from apps.engagement.serializers import FaithReflectSerializer
from apps.engagement.views import _active_relationship


def _practices_for(user):
    """Active practices for the user's tradition plus the universal ones."""
    tradition = services.resolve_tradition(user)
    return (
        FaithPractice.objects.filter(is_active=True)
        .filter(tradition__in=["", tradition])
        .order_by("order", "created_at")
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def faith_today(request):
    """Today's reading, the practice checklist, and the caller's progress."""
    day = today_key()
    reading = services.todays_reading(request.user)

    done_keys = set(
        FaithPracticeLog.objects.filter(user=request.user, date_key=day).values_list(
            "practice__key", flat=True
        )
    )
    practices = [
        {
            "key": p.key,
            "label": p.label,
            "icon": p.icon,
            "completed": p.key in done_keys,
        }
        for p in _practices_for(request.user)
    ]

    reflected = FaithReflection.objects.filter(user=request.user, date_key=day).exists()

    return Response(
        {
            "date_key": day,
            "tradition": services.resolve_tradition(request.user),
            "reading": (
                {
                    "id": str(reading.id),
                    "title": reading.title,
                    "reference": reading.reference,
                    "body": reading.body,
                    "reflection_prompt": reading.reflection_prompt,
                }
                if reading
                else None
            ),
            "practices": practices,
            "reflected": reflected,
        }
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def complete_practice(request):
    """Check off one practice for today. Idempotent; awards points once."""
    key = (request.data.get("practice_key") or "").strip()
    if not key:
        return Response(
            {"detail": "practice_key is required."}, status=status.HTTP_400_BAD_REQUEST
        )

    practice = (
        FaithPractice.objects.filter(is_active=True, key=key)
        .filter(tradition__in=["", services.resolve_tradition(request.user)])
        .first()
    )
    if practice is None:
        return Response(
            {"detail": "Unknown practice."}, status=status.HTTP_404_NOT_FOUND
        )

    day = today_key()
    relationship = _active_relationship(request.user)
    log, created = FaithPracticeLog.objects.get_or_create(
        user=request.user,
        practice=practice,
        date_key=day,
        defaults={"relationship": relationship},
    )
    if not created:
        return Response({"completed": True, "points_awarded": 0})

    awarded = services.award_points(
        request.user, relationship, "faith_practice", ref_id=log.id, day_key=day
    )
    services.touch_streak(request.user, day_key=day)
    return Response(
        {"completed": True, "points_awarded": awarded},
        status=status.HTTP_201_CREATED,
    )


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def reflect(request):
    """Save a private, encrypted reflection on today's reading."""
    serializer = FaithReflectSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    day = today_key()
    if FaithReflection.objects.filter(user=request.user, date_key=day).exists():
        return Response(
            {"detail": "Already reflected today.", "points_awarded": 0},
            status=status.HTTP_200_OK,
        )

    relationship = _active_relationship(request.user)
    reading = services.todays_reading(request.user)
    reflection = FaithReflection.objects.create(
        user=request.user,
        relationship=relationship,
        reading=reading,
        date_key=day,
        text=serializer.validated_data["text"],
    )

    awarded = services.award_points(
        request.user, relationship, "faith_reflection", ref_id=reflection.id, day_key=day
    )
    services.touch_streak(request.user, day_key=day)
    return Response(
        {"reflected": True, "points_awarded": awarded},
        status=status.HTTP_201_CREATED,
    )
