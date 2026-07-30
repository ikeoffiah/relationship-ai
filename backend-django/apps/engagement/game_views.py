"""
API views for couple games (Know Your Partner and the shared games engine).

Games are a two-person feature — every route resolves the caller's own active
relationship from ``request.user`` (no IDOR surface). Spicy packs additionally
require the caller to be age-verified.
"""

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.engagement import games, services
from apps.engagement.models import GameConsent, GamePack, GamePlay, GameQuestion
from apps.engagement.views import _active_relationship, _display_name, _partner_of


def _needs_relationship():
    return Response(
        {"message": "Games need an active partner connection.", "code": "no_active_relationship"},
        status=status.HTTP_409_CONFLICT,
    )


def _spicy_unlocked(user, relationship) -> bool:
    """Spicy packs unlock only when BOTH partners are age-verified AND both have
    opted in — a symmetric, consensual gate."""
    if relationship is None:
        return False
    partner = _partner_of(relationship, user)
    if partner is None:
        return False
    if not (getattr(user, "age_verified", False) and getattr(partner, "age_verified", False)):
        return False
    opted_in = set(
        GameConsent.objects.filter(
            relationship=relationship, spicy_opt_in=True
        ).values_list("user_id", flat=True)
    )
    return user.id in opted_in and partner.id in opted_in


def _visible_packs(user, relationship):
    """Active packs, excluding spicy ones unless the couple has unlocked them."""
    qs = GamePack.objects.filter(is_active=True)
    if not _spicy_unlocked(user, relationship):
        qs = qs.exclude(category="spicy")
    return qs


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def game_list(request):
    """Active packs the caller can play, each with their progress."""
    relationship = _active_relationship(request.user)
    partner = _partner_of(relationship, request.user)
    packs = []
    for pack in _visible_packs(request.user, relationship):
        prog = games.pack_progress(pack, relationship, request.user, partner)
        packs.append(
            {
                "key": pack.key,
                "title": pack.title,
                "description": pack.description,
                "game_type": pack.game_type,
                "category": pack.category,
                "question_count": prog["total"],
                "i_complete": prog["i_complete"],
                "partner_complete": prog["partner_complete"],
                "revealed": prog["revealed"],
            }
        )
    return Response({"games": packs, "has_partner": relationship is not None})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def game_detail(request, key):
    """A pack's questions plus the caller's progress, and — once both partners
    finish a scored game — the full reveal with scores."""
    pack = _get_visible_pack_or_404(request, key)
    if pack is None:
        return Response({"message": "Game not found."}, status=status.HTTP_404_NOT_FOUND)

    relationship = _active_relationship(request.user)
    partner = _partner_of(relationship, request.user)
    prog = games.pack_progress(pack, relationship, request.user, partner)

    my_plays = {
        p.question_id: p
        for p in GamePlay.objects.filter(pack=pack, user=request.user)
    }
    questions = [
        {
            "id": str(q.id),
            "prompt": q.prompt,
            "options": q.options,
            "my_answer": (my_plays[q.id].self_answer if q.id in my_plays else None),
            "my_guess": (my_plays[q.id].guess_answer if q.id in my_plays else None),
        }
        for q in pack.questions.all()
    ]

    body = {
        "key": pack.key,
        "title": pack.title,
        "game_type": pack.game_type,
        "category": pack.category,
        "is_scored": pack.is_scored,
        "has_partner": relationship is not None,
        "partner_name": _display_name(partner) if partner else None,
        "progress": prog,
        "questions": questions,
    }
    if prog["revealed"] and pack.is_scored:
        body["reveal"] = _reveal_for(pack, request.user, partner)
    return Response(body)


def _reveal_for(pack, user, partner):
    """The right reveal for the pack's mechanic: agreement for This-or-That,
    otherwise the guess-your-partner reveal."""
    if pack.is_agreement_game:
        return games.build_agreement_reveal(pack, user, partner)
    return games.build_reveal(pack, user, partner)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def game_answer(request, key):
    """Submit one answer (and, for a guessing game, a guess of the partner)."""
    relationship = _active_relationship(request.user)
    if relationship is None:
        return _needs_relationship()

    pack = _get_visible_pack_or_404(request, key)
    if pack is None:
        return Response({"message": "Game not found."}, status=status.HTTP_404_NOT_FOUND)

    try:
        question = GameQuestion.objects.get(id=request.data.get("question_id"), pack=pack)
    except (GameQuestion.DoesNotExist, ValueError, TypeError):
        return Response({"message": "Question not found in this game."}, status=status.HTTP_404_NOT_FOUND)

    err, self_answer, guess_answer = games.validate_answer(
        question, request.data.get("self_answer"), request.data.get("guess_answer"), pack.is_scored
    )
    if err:
        return Response({"message": err}, status=status.HTTP_400_BAD_REQUEST)

    partner = _partner_of(relationship, request.user)
    was_complete = games.pack_progress(pack, relationship, request.user, partner)["i_complete"]

    GamePlay.objects.update_or_create(
        user=request.user,
        question=question,
        defaults={
            "relationship": relationship,
            "pack": pack,
            "self_answer": self_answer,
            "guess_answer": guess_answer,
        },
    )

    prog = games.pack_progress(pack, relationship, request.user, partner)
    just_completed = prog["i_complete"] and not was_complete

    reveal = None
    if just_completed:
        # Completing a pack is a daily activity: award points + advance streak.
        services.record_daily_activity(request.user, relationship, "game_completed")
        # If the partner had already finished, results are now ready for both.
        if prog["revealed"]:
            if partner is not None:
                services.notify(
                    partner.id,
                    "game_ready",
                    title=f"Your '{pack.title}' results are ready 🎉",
                    body=f"{_display_name(request.user)} finished — see how well you know each other.",
                    data={"deep_link": "/engagement/games", "game_key": pack.key},
                )
            if pack.is_scored:
                reveal = _reveal_for(pack, request.user, partner)
        elif partner is not None:
            # Nudge the partner to play so the reveal can happen.
            services.notify(
                partner.id,
                "game_ready",
                title=f"{_display_name(request.user)} played '{pack.title}'",
                body="Play it too to unlock your results.",
                data={"deep_link": "/engagement/games", "game_key": pack.key},
            )

    return Response(
        {"progress": prog, "just_completed": just_completed, "reveal": reveal},
        status=status.HTTP_200_OK,
    )


def _get_visible_pack_or_404(request, key):
    pack = GamePack.objects.filter(key=key, is_active=True).first()
    if pack is None:
        return None
    if pack.category == "spicy":
        relationship = _active_relationship(request.user)
        if not _spicy_unlocked(request.user, relationship):
            return None  # hidden until the couple unlocks spicy
    return pack


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def spicy_consent(request):
    """The couple's spicy opt-in state, and the caller's toggle.

    GET  -> {you, partner, both_age_verified, unlocked}
    POST {enabled: bool} -> records the caller's opt-in (requires age-verified).
    """
    relationship = _active_relationship(request.user)

    # A read has an answer even with nobody to be mutual with, and the answer is
    # "not unlocked". This used to 409 for a solo user, which made a perfectly
    # ordinary state — no partner yet — arrive at the client as an exception:
    # a stack trace in the console every time someone solo opened games or the
    # chat, and callers forced to infer "locked" from a failure. Worse, it made
    # a real network problem indistinguishable from being single.
    #
    # POST still needs a relationship. You cannot record half of a mutual
    # consent when there is no other half.
    if relationship is None:
        if request.method == "POST":
            return _needs_relationship()
        return Response(
            {
                "you": False,
                "partner": False,
                "both_age_verified": False,
                "unlocked": False,
            }
        )

    partner = _partner_of(relationship, request.user)

    if request.method == "POST":
        if not getattr(request.user, "age_verified", False):
            return Response(
                {"message": "Verify your age to enable spicy games.", "code": "age_verification_required"},
                status=status.HTTP_403_FORBIDDEN,
            )
        raw = request.data.get("enabled", False)
        enabled = raw if isinstance(raw, bool) else str(raw).strip().lower() in ("true", "1", "yes")
        GameConsent.objects.update_or_create(
            relationship=relationship,
            user=request.user,
            defaults={"spicy_opt_in": enabled},
        )

    opted = dict(
        GameConsent.objects.filter(relationship=relationship).values_list("user_id", "spicy_opt_in")
    )
    both_verified = getattr(request.user, "age_verified", False) and (
        partner is not None and getattr(partner, "age_verified", False)
    )
    return Response(
        {
            "you": bool(opted.get(request.user.id, False)),
            "partner": bool(opted.get(getattr(partner, "id", None), False)),
            "both_age_verified": both_verified,
            "unlocked": _spicy_unlocked(request.user, relationship),
        }
    )
