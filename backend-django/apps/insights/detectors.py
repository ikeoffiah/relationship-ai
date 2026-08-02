"""Noticing a pattern a couple is too close to see.

One detector so far, and it is deliberately the one that needs no consent flow:
``recurring_theme`` reads the couple's **shared thread**, which both partners
watched happen, and says only the *shape* of what it found.

``perception_gap`` is the headline and is not here, for a reason worth writing
down rather than discovering later: it compares two partners' private accounts
of the same event, and there are currently **no sessions in the database at
all**. Writing it would mean writing a detector against an empty table with no
way to know whether it works — and it is the one detector that cannot exist
without reading both private sides, so it is also the one that most needs to be
right. It waits for data and for the consent flow in
``docs/relationship-insights.md`` §5.

**Shape, not content.** Everything here produces a sentence that is true of both
partners and discloses nothing either of them did not already see:

    ✅ "The same disagreement about evenings has come back three times."
    ❌ "Grace felt dismissed when you cancelled on Saturday."

That is why a shared-thread insight can be shown to both without a consent
step — not because consent was waived, but because there is nothing in it to
consent to. The moment a detector reads a private session, that stops being
true and §5 applies.
"""

from __future__ import annotations

import logging
from datetime import timedelta

from django.utils import timezone

log = logging.getLogger(__name__)

#: How far back a theme is looked for. Long enough that "recurring" means
#: something, short enough to be about now rather than about last spring.
THEME_WINDOW_DAYS = 60

#: Below this many ruptures there is no pattern to find — two arguments about
#: different things is a fortnight, not a theme.
MIN_RUPTURES_FOR_A_THEME = 3

#: Below this the insight is not stored at all. An insight is a claim about
#: somebody's relationship, and a hedged claim is worse than silence.
MIN_CONFIDENCE = 0.6

_THEME_SYSTEM = (
    "You are reading the arguments a couple has had over the last few weeks, "
    "and deciding whether the same disagreement keeps coming back.\n"
    "\n"
    "A recurring theme is one *subject* returning — money, whose turn it is, "
    "time with family, feeling unheard — not simply several arguments. Couples "
    "argue about different things and that is ordinary; this exists to notice "
    "when it is the same thing wearing different clothes.\n"
    "\n"
    "If you find one, name the subject in a short phrase, in the second person "
    "plural, addressed to both of them. It will be shown to both partners, so "
    "it must be true of the pair and must not quote either of them, blame "
    "either of them, or repeat anything one of them said. 'How evenings get "
    "decided' — not 'you keep cancelling on her'.\n"
    "\n"
    "Most couples do not have one. Say so rather than inventing a theme to be "
    "helpful.\n"
    "\n"
    "The test that matters: a subject that would fit almost any couple who "
    "argue is not a finding. 'Communication', 'responsibility for shared "
    "tasks', 'not feeling heard', 'respect' — these are true of everybody "
    "and so tell this couple nothing. If your theme could be said to the "
    "couple next door, answer none. A real theme is specific enough that "
    "these two would recognise it and a stranger would not have guessed it.\n"
    "\n"
    "Name which arguments the subject actually appears in, by number. If it "
    "is not genuinely present in at least three of them there is no theme. "
    "Abstracting several different arguments up to one word they have in "
    "common is the mistake this instruction exists to prevent.\n"
    "\n"
    "Reply in exactly this format and nothing else:\n"
    "THEME: none\n"
    "or\n"
    "THEME: <the subject, at most eight words>\n"
    "ARGUMENTS: <the numbers it appears in, comma separated>\n"
    "CONFIDENCE: <0.0 to 1.0>"
)


def _parse_theme(raw: str | None) -> tuple[str, float, int] | None:
    """``(theme, confidence, arguments_cited)`` or None.

    The citation is the load-bearing part. Confidence is a self-report and a
    model asked how sure it is will say 0.8 whatever it has found; how many
    arguments it can actually point at is a claim that can be checked.
    """
    if not raw:
        return None
    theme, confidence, cited = None, 0.0, 0
    for line in raw.splitlines():
        lowered = line.strip().lower()
        if lowered.startswith("theme:"):
            value = line.split(":", 1)[1].strip()
            theme = None if value.lower() in ("none", "") else value
        elif lowered.startswith("confidence:"):
            try:
                confidence = max(0.0, min(1.0, float(lowered.split(":", 1)[1].strip())))
            except (TypeError, ValueError):
                confidence = 0.0
        elif lowered.startswith("arguments:"):
            cited = len(
                [
                    part
                    for part in line.split(":", 1)[1].replace(" ", "").split(",")
                    if part.strip().isdigit()
                ]
            )
    if theme is None:
        return None
    return theme, confidence, cited


def recurring_theme(relationship) -> dict | None:
    """Is the same disagreement coming back? Shape only.

    Reads the *assessed* ruptures rather than looking for sharp words itself —
    so this inherits the comprehension work rather than reintroducing a
    lexicon, and costs one call over a couple's whole recent history rather
    than one per exchange.

    Returns ``{"theme": str, "confidence": float}`` or None. None is the normal
    answer and the prompt says so: most couples do not have a recurring theme,
    and a detector that finds one anyway is worse than no detector.
    """
    from apps.chat.assist import _complete, message_text
    from apps.chat.models import CoupleMessage
    from apps.personalization.connection import RUPTURE_CONFIDENCE
    from apps.personalization.models import RuptureAssessment

    since = timezone.now() - timedelta(days=THEME_WINDOW_DAYS)
    ruptures = list(
        RuptureAssessment.objects.filter(
            relationship=relationship,
            started_at__gte=since,
            is_rupture=True,
            confidence__gte=RUPTURE_CONFIDENCE,
        ).order_by("started_at")
    )
    if len(ruptures) < MIN_RUPTURES_FOR_A_THEME:
        return None

    # Each argument, as its own block, so the model can compare them rather
    # than read one long undifferentiated stream.
    blocks = []
    for index, rupture in enumerate(ruptures, start=1):
        rows = (
            CoupleMessage.objects.filter(
                relationship=relationship,
                created_at__gte=rupture.started_at,
                created_at__lte=rupture.ended_at,
                deleted_at__isnull=True,
            )
            .select_related("media")
            .order_by("created_at")
        )
        lines = [message_text(row) for row in rows]
        lines = [line for line in lines if line]
        if lines:
            blocks.append(f"Argument {index}:\n" + "\n".join(lines))

    if len(blocks) < MIN_RUPTURES_FOR_A_THEME:
        return None

    parsed = _parse_theme(
        _complete(_THEME_SYSTEM, "\n\n".join(blocks), 12.0, max_tokens=60)
    )
    if parsed is None:
        return None

    theme, confidence, cited = parsed

    # It has to be able to point at the arguments. Three unrelated rows — a
    # door left unlocked, a rude brother, an untaxed car — came back as
    # "responsibility for shared tasks" at 0.8, which is true of every couple
    # who has ever argued and tells this one nothing. Abstracting different
    # rows up to a word they have in common is the failure this guards.
    if cited < MIN_RUPTURES_FOR_A_THEME:
        log.info(
            "insight_too_thin relationship=%s cited=%s", relationship.id, cited
        )
        return None

    if confidence < MIN_CONFIDENCE:
        log.info(
            "insight_below_confidence relationship=%s confidence=%.2f",
            relationship.id,
            confidence,
        )
        return None
    return {"theme": theme, "confidence": confidence}
