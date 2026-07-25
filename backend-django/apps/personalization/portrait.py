"""
Relationship portrait — the first-open "this app gets me" moment.

Turns the onboarding answers already captured on ``UserProfile`` into a
specific, personal reading of how the user shows up in relationships. It is
deterministic (keyed on attachment style, enriched by communication style and
context) rather than LLM-generated, so it is reliable, testable, needs no API
key, and — critically — every line is traceable to an answer the user gave.

Design rule: it must beat the horoscope test. If two different attachment
profiles could be swapped without the user noticing, it is generic and worthless.
The content below is written to be distinct per style.
"""

from typing import Optional

# Per-attachment-style content. The four styles match the RSQ scoring in
# ``apps.personalization.tasks``: secure, anxious-preoccupied,
# dismissive-avoidant, fearful-avoidant.
_STYLES = {
    "secure": {
        "archetype": "The Secure Anchor",
        "headline": "You can get close without losing yourself — rarer than you'd think.",
        "summary": (
            "You tend to trust that a bond can hold weight. You can say what you "
            "need, hear a hard thing without it becoming a threat, and come back "
            "after a rough patch. That steadiness is your quiet superpower."
        ),
        "what_helps": (
            "Honest, direct conversation — you'd rather handle the real thing "
            "than tiptoe around it."
        ),
        "what_trips_you_up": (
            "Assuming your partner regulates conflict as easily as you do. What "
            "feels like 'just talking it out' to you can land as a confrontation "
            "to them."
        ),
        "growth_edge": (
            "Slowing down for a partner whose alarm system is louder than yours."
        ),
        "likely_friction": [
            "your calm reading as indifference during big decisions",
            "a partner needing more reassurance than you'd think to give",
            "quietly carrying more of the emotional steadying than gets noticed",
        ],
    },
    "anxious-preoccupied": {
        "archetype": "The Devoted Connector",
        "headline": "You love deeply, and you read the room before you read yourself.",
        "summary": (
            "Closeness is where you feel most alive — and most exposed. You're "
            "attuned to the smallest shifts in your partner's mood, which makes "
            "you deeply caring, and also quick to feel an alarm when things go "
            "quiet."
        ),
        "what_helps": (
            "A partner who names what they're feeling out loud — even the small "
            "stuff — so you're not left filling the silence with worst-case stories."
        ),
        "what_trips_you_up": (
            "Reading a delay or a short reply as rejection, and chasing "
            "reassurance in a way that can push away the very closeness you want."
        ),
        "growth_edge": (
            "Saying the scary thing early — 'I'm feeling disconnected' — before "
            "it hardens into a story about being unwanted."
        ),
        "likely_friction": [
            "needing reassurance faster than your partner thinks to offer it",
            "a distracted partner reading as 'something's wrong with us'",
            "text-message tone spiraling before you've talked in person",
        ],
    },
    "dismissive-avoidant": {
        "archetype": "The Independent",
        "headline": "You handle things yourself — sometimes before anyone knew there was a thing.",
        "summary": (
            "You value your autonomy and you're steady under pressure. Closeness "
            "is welcome, but too much intensity too fast can make you want room "
            "to breathe — that's self-protection, not indifference."
        ),
        "what_helps": (
            "A partner who gives you space without reading it as rejection, and "
            "lets closeness build at a pace that doesn't feel like pressure."
        ),
        "what_trips_you_up": (
            "Going quiet or 'handling it alone' when things get emotionally heavy, "
            "which can leave your partner feeling shut out."
        ),
        "growth_edge": (
            "Naming one feeling out loud instead of retreating to solve it privately."
        ),
        "likely_friction": [
            "needing space that your partner reads as pulling away",
            "big feelings landing as 'too much' when you'd rather stay level",
            "being asked to talk right now when you need time first",
        ],
    },
    "fearful-avoidant": {
        "archetype": "The Guarded Heart",
        "headline": "You want closeness and brace for it at the same time.",
        "summary": (
            "You feel things intensely and long for deep connection — but a part "
            "of you stays on guard, because closeness has felt unsafe before. "
            "That push-pull isn't a flaw; it's a system that learned to protect you."
        ),
        "what_helps": (
            "A partner who stays consistent and patient, and doesn't take a sudden "
            "pullback personally — steadiness is what convinces your guard it can "
            "stand down."
        ),
        "what_trips_you_up": (
            "Wanting to get close and then needing to retreat when it gets real, "
            "which can feel confusing to both of you."
        ),
        "growth_edge": (
            "Naming the mixed feeling itself: 'I want to be close and I'm scared — "
            "both are true right now.'"
        ),
        "likely_friction": [
            "hot-and-cold cycles that leave you both unsure where you stand",
            "conflict feeling higher-stakes than the moment calls for",
            "trust taking longer to rebuild after a rupture",
        ],
    },
}

_COMMUNICATION_NOTES = {
    "assertive": (
        "You tend to say what you mean directly — a real asset, as long as your "
        "partner's style can meet it."
    ),
    "passive": (
        "You often hold back to keep the peace, which can mean needs go unspoken "
        "until they've quietly built up."
    ),
    "analytical": (
        "You process by thinking it through — give yourself permission to share "
        "the half-formed version out loud too."
    ),
    "expressive": (
        "You feel out loud and in the moment — powerful, and worth pairing with a "
        "pause when things get heated."
    ),
    "avoidant": (
        "You tend to sidestep confrontation — your growth is staying in the room "
        "for the uncomfortable 60 seconds."
    ),
}


def _context_note(profile) -> str:
    """A line grounded in the user's actual relationship context, when present."""
    parts = []
    if profile.cohabiting:
        parts.append(
            "Living together, a lot of this shows up in everyday logistics — "
            "chores, time, money — more than in big dramatic moments."
        )
    elif (profile.relationship_duration_months or 0) and profile.relationship_duration_months < 18:
        parts.append(
            "Early on, these patterns are still forming — noticing them now is a "
            "real head start."
        )
    if (profile.children_count or 0) > 0:
        parts.append(
            "With kids in the picture, protected time for just the two of you is "
            "the thing that quietly erodes first."
        )
    return " ".join(parts)


def build_portrait(profile) -> dict:
    """Build the relationship portrait payload from a ``UserProfile``.

    Returns ``ready=False`` when we don't yet have an attachment style (e.g.
    onboarding not finished) so the client can show a graceful state instead of
    a generic reading.
    """
    style_key = (profile.attachment_style or "").strip().lower()
    content = _STYLES.get(style_key)
    if content is None:
        return {
            "ready": False,
            "message": "Finish onboarding to see your relationship portrait.",
        }

    comm_key = (profile.communication_style_self_report or "").strip().lower()
    communication_note: Optional[str] = _COMMUNICATION_NOTES.get(comm_key)

    return {
        "ready": True,
        "attachment_style": style_key,
        "archetype": content["archetype"],
        "headline": content["headline"],
        "summary": content["summary"],
        "what_helps": content["what_helps"],
        "what_trips_you_up": content["what_trips_you_up"],
        "growth_edge": content["growth_edge"],
        "likely_friction": content["likely_friction"],
        "communication_note": communication_note,
        "context_note": _context_note(profile) or None,
    }
