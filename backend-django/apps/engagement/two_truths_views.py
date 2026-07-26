"""
API for Two Truths & a Lie.

* ``GET  two-truths``        — the caller's round state (their statements, the
  partner's statements to guess, and — once both authored + both guessed — the
  reveal).
* ``POST two-truths/author`` — write/replace my three statements + which is the
  lie.
* ``POST two-truths/guess``  — guess which of my partner's statements is the lie
  (requires the partner to have authored first).
* ``POST two-truths/reset``  — clear both partners' plays to start a fresh round.

All routes resolve the caller's own active relationship from ``request.user`` —
never from the client — so there's no IDOR surface. The game needs a partner.
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.engagement import services, two_truths
from apps.engagement.models import TwoTruthsPlay
from apps.engagement.views import _active_relationship, _partner_of


def _plays(relationship, user, partner):
    mine = TwoTruthsPlay.objects.filter(relationship=relationship, user=user).first()
    theirs = (
        TwoTruthsPlay.objects.filter(relationship=relationship, user=partner).first()
        if partner
        else None
    )
    return mine, theirs


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def state(request):
    relationship = _active_relationship(request.user)
    partner = _partner_of(relationship, request.user)
    mine, theirs = _plays(relationship, request.user, partner)
    body = two_truths.build_state(mine, theirs)
    body["has_partner"] = relationship is not None and partner is not None
    body["partner_name"] = (
        (partner.full_name or partner.email.split("@")[0]) if partner else None
    )
    return Response(body)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def author(request):
    relationship = _active_relationship(request.user)
    if relationship is None:
        return Response(
            {"detail": "Two Truths is a game for two — invite your partner first."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    err, statements = two_truths.validate_statements(request.data.get("statements"))
    if err:
        return Response({"detail": err}, status=status.HTTP_400_BAD_REQUEST)
    err, lie_index = two_truths.validate_index(request.data.get("lie_index"))
    if err:
        return Response({"detail": err}, status=status.HTTP_400_BAD_REQUEST)

    TwoTruthsPlay.objects.update_or_create(
        relationship=relationship,
        user=request.user,
        defaults={"statements": statements, "lie_index": lie_index},
    )
    partner = _partner_of(relationship, request.user)
    mine, theirs = _plays(relationship, request.user, partner)
    # Nudge the partner to play once I've authored.
    if theirs is None and partner is not None:
        services.notify(
            partner.id,
            "game_ready",
            title="Two Truths & a Lie 🕵️",
            body=f"{_short(request.user)} wrote theirs — can you spot the lie?",
            data={"deep_link": "/engagement/two-truths"},
        )
    return Response(two_truths.build_state(mine, theirs), status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def guess(request):
    relationship = _active_relationship(request.user)
    partner = _partner_of(relationship, request.user)
    mine, theirs = _plays(relationship, request.user, partner)

    if theirs is None:
        return Response(
            {"detail": "Your partner hasn't written their statements yet."},
            status=status.HTTP_409_CONFLICT,
        )
    if mine is None:
        return Response(
            {"detail": "Write your own three statements first."},
            status=status.HTTP_409_CONFLICT,
        )

    err, guess_index = two_truths.validate_index(request.data.get("guess_index"))
    if err:
        return Response({"detail": err}, status=status.HTTP_400_BAD_REQUEST)

    mine.guess_index = guess_index
    mine.save(update_fields=["guess_index"])

    state_now = two_truths.build_state(mine, theirs)
    # If that completed the round, award both and nudge the partner.
    if state_now["revealed"]:
        services.record_daily_activity(request.user, relationship, "game_completed")
        if partner is not None:
            services.notify(
                partner.id,
                "game_ready",
                title="Two Truths results are in 🎉",
                body="See who caught whom.",
                data={"deep_link": "/engagement/two-truths"},
            )
    return Response(state_now, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def reset(request):
    """Clear both partners' plays so the couple can start a fresh round."""
    relationship = _active_relationship(request.user)
    if relationship is not None:
        TwoTruthsPlay.objects.filter(relationship=relationship).delete()
    return Response({"reset": True})


def _short(user, n: int = 24) -> str:
    name = user.full_name or user.email.split("@")[0]
    return name if len(name) <= n else name[: n - 1] + "…"
