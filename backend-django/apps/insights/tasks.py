"""Producing insights, nightly, with the safety rules from the spec.

This file previously imported ``apps.insights.jobs`` and ``apps.core``, neither
of which has ever existed in this repository, and was not a task at all — its
only effect on the product was killing Celery during autodiscovery. It was
deleted. This is the real one.

See ``docs/relationship-insights.md``. Two rules from §7 live here rather than
in the detector, because they are about whether a couple should be shown
anything at all rather than about what was found:

**Not in the middle of it.** An insight naming a recurring argument, delivered
the morning after one, is a prosecution. Held while a rupture is open.

**Not at all where there are abuse signals**, for ninety days from the last
one, resetting on every new signal. Elapsed time only and never a behavioural
condition — repair signals are things a controlling partner can perform and can
pressure the other into performing, so "demonstrate repair to restore access"
would be instructions for looking repaired handed to the person the rule exists
to protect against. Nobody can perform elapsed time.
"""

from __future__ import annotations

import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)

#: How long an abuse signal holds insights back. Matches the decay that clears
#: policy suppression elsewhere, so this is in character rather than a special
#: case, and any new signal restarts it.
ABUSE_QUIET_DAYS = 90

#: An insight is not offered while an argument is still open.
RUPTURE_QUIET_DAYS = 3

#: Insights go stale. A theme from three months ago is a claim about a couple
#: who may have fixed it.
INSIGHT_TTL_DAYS = 30


def _abuse_signalled_recently(relationship) -> bool:
    """Has anything in the last ninety days looked like coercion?

    Reads the couple's own thread through the same vocabulary the read-coaching
    referral uses, so "this looked like abuse" has one answer across the
    product. Fails *closed* — an error here means no insights, because the cost
    of being wrong in the other direction is handing a controlling partner a
    tool.
    """
    from apps.chat.assist import _ABUSE_SIGNALS, message_text
    from apps.chat.models import CoupleMessage

    try:
        since = timezone.now() - timedelta(days=ABUSE_QUIET_DAYS)
        rows = (
            CoupleMessage.objects.filter(
                relationship=relationship,
                created_at__gte=since,
                deleted_at__isnull=True,
            )
            .select_related("media")
            .only("body", "kind", "media")
        )
        for row in rows.iterator():
            lowered = message_text(row).lower()
            if any(signal in lowered for signal in _ABUSE_SIGNALS):
                return True
        return False
    except Exception:
        logger.warning(
            "insight_abuse_check_failed relationship=%s", relationship.id, exc_info=True
        )
        return True


def _rupture_is_open(relationship) -> bool:
    """Are they in the middle of something right now?"""
    from apps.personalization.connection import RUPTURE_CONFIDENCE
    from apps.personalization.models import RuptureAssessment

    try:
        return RuptureAssessment.objects.filter(
            relationship=relationship,
            ended_at__gte=timezone.now() - timedelta(days=RUPTURE_QUIET_DAYS),
            is_rupture=True,
            confidence__gte=RUPTURE_CONFIDENCE,
        ).exists()
    except Exception:
        logger.warning(
            "insight_rupture_check_failed relationship=%s",
            relationship.id,
            exc_info=True,
        )
        return True


def may_surface(relationship) -> bool:
    """Whether this couple may be shown an insight at all today."""
    return not _abuse_signalled_recently(relationship) and not _rupture_is_open(
        relationship
    )


@shared_task(name="insights.synthesise")
def synthesise_insights() -> int:
    """Find what is worth noticing, for every active couple.

    Nightly and batched — the detector reads a couple's whole recent history in
    one call, so this is roughly one call per couple per night, and none of it
    is anywhere near a request somebody is waiting on.

    Only shape-only insights are produced so far, built from the shared thread.
    Both `shared_with_*` flags are set on those, and that is not a consent
    waiver: a shape says only that a pattern exists, in words true of both
    partners, about a thread they both watched. There is nothing in it to
    consent to. The moment a detector reads a private session that stops being
    true and §5 of the spec applies.
    """
    from apps.insights.detectors import recurring_theme
    from apps.insights.models import RelationshipInsight
    from apps.relationships.models import Relationship

    written = 0
    for relationship in Relationship.objects.filter(status="active").iterator():
        try:
            if not may_surface(relationship):
                continue

            found = recurring_theme(relationship)
            if found is None:
                continue

            RelationshipInsight.objects.update_or_create(
                relationship=relationship,
                type="recurring_theme",
                defaults={
                    "theme": found["theme"],
                    "confidence": found["confidence"],
                    # Shape only. The narrative halves stay empty until there
                    # is a consent flow to gate them with.
                    "a_narrative_summary": "",
                    "b_narrative_summary": "",
                    "synthesis": "",
                    "suggested_intervention": "",
                    "shared_with_a": True,
                    "shared_with_b": True,
                    "approved_for_joint": False,
                    "expires_at": timezone.now() + timedelta(days=INSIGHT_TTL_DAYS),
                },
            )
            written += 1
        except Exception:
            logger.warning(
                "insight_synthesis_failed relationship=%s",
                relationship.id,
                exc_info=True,
            )

    logger.info("insights_synthesised count=%s", written)
    return written
