from __future__ import annotations
import uuid
from typing import List
from django.db import transaction
from apps.relationships.models import Relationship
from apps.sessions.models import LangGraphSession
from apps.insights.models import RelationshipInsight

@transaction.atomic
def insight_synthesis_job(relationship_id: uuid.UUID) -> None:
    """Generate insights for a relationship.

    Fetch the most recent individual sessions for each partner, run all detection
    modules, upsert ``RelationshipInsight`` records, and refresh the relationship
    vector embedding.

    Neither ``apps.insights.jobs`` nor ``apps.core`` exists — neither has ever
    existed in this repository — so calling this raises ImportError. That is
    the honest state and it is left visible rather than stubbed.

    What has changed is where the failure lands. These five imports used to sit
    at module scope, and Celery autodiscovers a ``tasks`` module from every
    installed app, so importing this unfinished file was the first thing a
    worker did and the last: it died during autodiscovery, before registering a
    single task. Every background job in the product — voice transcription,
    media moderation, the nightly connection score — silently did nothing, and
    the only symptom was work that never happened. Nothing in this module is
    even a ``shared_task``; it took the worker down without contributing one.
    """
    from apps.insights.jobs.perception_misalignment import run as perception_misalignment
    from apps.insights.jobs.recurring_conflict_theme import run as recurring_conflict_theme
    from apps.insights.jobs.emotional_needs_gap import run as emotional_needs_gap
    from apps.insights.jobs.progress_signal import run as progress_signal
    from apps.insights.jobs.flourishing_pattern import run as flourishing_pattern
    from apps.core.vector import update_relationship_vectors

    relationship = Relationship.objects.select_for_update().get(id=relationship_id)
    sessions_a = LangGraphSession.objects.filter(relationship=relationship, user=relationship.partner_a).order_by('-created_at')[:10]
    sessions_b = LangGraphSession.objects.filter(relationship=relationship, user=relationship.partner_b).order_by('-created_at')[:10]

    insights: List[RelationshipInsight] = []
    for module in [
        perception_misalignment,
        recurring_conflict_theme,
        emotional_needs_gap,
        progress_signal,
        flourishing_pattern,
    ]:
        results = module(sessions_a, sessions_b)
        insights.extend(results)

    for insight in insights:
        RelationshipInsight.objects.update_or_create(
            relationship=relationship,
            type=insight.type,
            defaults={
                "theme": insight.theme,
                "confidence": insight.confidence,
                "a_narrative_summary": getattr(insight, "a_narrative_summary", ""),
                "b_narrative_summary": getattr(insight, "b_narrative_summary", ""),
                "synthesis": getattr(insight, "synthesis", ""),
                "suggested_intervention": getattr(insight, "suggested_intervention", ""),
            },
        )

    update_relationship_vectors(relationship.id)
