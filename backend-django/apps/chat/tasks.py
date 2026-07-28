"""Background work for the couple thread.

Everything here is deliberately off the request path. The send-time check has a
2.5s budget and most sends never reach a model at all; summarising costs a full
extra round-trip, so it happens after the fact, on a worker.
"""

import logging

from celery import shared_task

from .models import CoupleMessage, Relationship, ThreadSummary

log = logging.getLogger(__name__)

# Refresh once the thread has moved on by this many messages. Low enough that
# the summary stays current, high enough that a chatty evening does not queue a
# summarisation per message.
REFRESH_EVERY_MESSAGES = 20

# How much of the tail the summariser reads.
SUMMARISE_WINDOW = 60

_SUMMARY_SYSTEM = (
    "Summarise this couple's recent conversation for an assistant that will "
    "use it as background. Capture recurring themes, what each partner seems "
    "to need, anything that is clearly a sore spot, and the overall warmth or "
    "strain of the exchange. Be factual and brief — at most 120 words. "
    "Do not give advice, do not take a side, and do not quote messages."
)


def summary_is_stale(relationship) -> bool:
    total = CoupleMessage.objects.filter(
        relationship=relationship, deleted_at__isnull=True
    ).count()
    summary = ThreadSummary.objects.filter(relationship=relationship).first()
    covered = summary.covered_message_count if summary else 0
    return total - covered >= REFRESH_EVERY_MESSAGES


@shared_task(name="chat.refresh_thread_summary")
def refresh_thread_summary(relationship_id) -> str | None:
    """Rewrite the rolling summary for one thread."""
    from . import assist

    relationship = Relationship.objects.filter(id=relationship_id).first()
    if relationship is None:
        return None
    if not assist.settings_for(relationship).assist_enabled:
        return None

    messages = list(
        CoupleMessage.objects.filter(
            relationship=relationship,
            deleted_at__isnull=True,
            kind=CoupleMessage.KIND_TEXT,
        ).order_by("-created_at")[:SUMMARISE_WINDOW]
    )
    if not messages:
        return None
    messages.reverse()

    transcript = "\n".join(f"{m.sender_id}: {m.body}" for m in messages if m.body)
    if not transcript:
        return None

    text = assist._complete(
        _SUMMARY_SYSTEM,
        transcript,
        timeout=20.0,  # generous: nobody is waiting on this
        max_tokens=200,
    )
    if not text:
        return None

    total = CoupleMessage.objects.filter(
        relationship=relationship, deleted_at__isnull=True
    ).count()
    ThreadSummary.objects.update_or_create(
        relationship=relationship,
        defaults={"summary": text, "covered_message_count": total},
    )
    log.info("thread_summary_refreshed relationship=%s", relationship_id)
    return text
