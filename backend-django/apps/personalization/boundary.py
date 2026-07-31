"""The one place anything about a person may cross toward their partner.

``behaviour.py`` rule 4 says a person's profile is never shown to their
partner. That rule is the single most important property in this system, and
until now it has been held up by careful authors remembering it. This module
makes it a function, so that holding the line is the default rather than an act
of vigilance, and so there is one thing to test.

**What may cross:** tone instructions for text being written *to* the person
they describe. "Lead with reassurance." "Leave them a way back in." These reach
their partner only in the sense that a well-phrased message does — the partner
never sees the instruction, only a message that landed better than it would
have.

**What may never cross:** any trait, score, tendency, signal name, label or
observation about a person, in any form, to anyone but that person.

The reason for being absolute about it: an inferred model of one partner,
surfaced to the other, is a manipulation manual. In the minority of couples
with a controlling dynamic it is a weapon. In a separation it is discoverable.
And on the day someone realises the app has been briefing their partner on
their psychology, the product is finished — correctly.

Being *derived from* someone's profile is not the test. Reaching them as a
claim about their partner is. A rewrite suggestion shaped by knowing the
recipient goes quiet under pressure is exactly the point of the feature; a
sentence telling their partner that they go quiet under pressure is the thing
this module exists to prevent.
"""

from __future__ import annotations

from . import behaviour


def phrasing_guidance_for(recipient_id) -> list[str]:
    """Tone directives for text that will be read by ``recipient_id``.

    The only thing permitted to cross between partners, and only in this
    direction: the guidance describes the person who will *read* the message,
    and is consumed by whatever writes that message.

    Callers must satisfy one condition, which no type system can enforce and
    which the tests assert instead: the return value may be injected into a
    prompt whose output goes to ``recipient_id``, and may not be returned to
    anyone else — not rendered, not logged into a shared record, not included
    in an insight the partner can read.
    """
    return behaviour.guidance_for(recipient_id)


def self_description_for(user_id) -> list[str]:
    """How a person's own tendencies are said back to them.

    Separate from :func:`phrasing_guidance_for` because the audience is
    different and the permission is different: this is a person reading about
    themselves, which they are entitled to do, and which is also the best
    correction signal the system will ever get. It must never be fetched on
    anyone's behalf but their own.
    """
    return [
        behaviour.SELF_DESCRIPTION[signal]
        for signal in behaviour.tendencies_for(user_id)
        if signal in behaviour.SELF_DESCRIPTION
    ]


def leaks(payload) -> list[str]:
    """Anything in ``payload`` that must not reach a partner. Empty is clean.

    A blunt instrument used by the tests and available to any endpoint that
    wants to assert its own output. It looks for the vocabulary of the profile
    — signal names and the exact sentences meant for the person themselves —
    on the principle that if the words appear at all, something has gone wrong
    upstream of wherever this is being called.

    It cannot catch a paraphrase, and is not meant to. It catches the failure
    that actually happens: a field added to a serializer without anyone
    thinking about who reads it.
    """
    text = _flatten(payload)
    found = []

    for signal in behaviour.SIGNALS:
        if signal in text:
            found.append(signal)

    for signal, sentence in behaviour.SELF_DESCRIPTION.items():
        # A distinctive fragment rather than the whole sentence: the leak worth
        # catching is a copy, and a copy keeps the middle of the sentence even
        # when something has trimmed the ends.
        fragment = sentence.split(",")[-1].strip().rstrip(".")
        if fragment and fragment in text:
            found.append(f"self_description:{signal}")

    return found


def _flatten(payload) -> str:
    """Every string anywhere in a nested response body, concatenated."""
    if payload is None:
        return ""
    if isinstance(payload, str):
        return payload
    if isinstance(payload, dict):
        return " ".join(
            _flatten(key) + " " + _flatten(value) for key, value in payload.items()
        )
    if isinstance(payload, (list, tuple, set)):
        return " ".join(_flatten(item) for item in payload)
    return str(payload)
