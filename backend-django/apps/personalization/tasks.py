import logging
from celery import shared_task
from django.utils import timezone
from apps.personalization.models import UserProfile

logger = logging.getLogger(__name__)

#: How many items a submission must contain before a prototype is assigned.
#:
#: Missing items default to a neutral 3, which is fine for one or two gaps and
#: meaningless for twenty — a mostly-empty submission scores every prototype at
#: 3.0 and the label becomes whichever key the dict happened to yield first.
MIN_ITEMS_TO_SCORE = 12

#: The Griffin & Bartholomew (1994) RSQ prototype key. Reverse-keyed items are
#: marked; everything is a mean so the four are comparable.
#:
#: See ``docs/engineering/rsq-scoring.md``. Only ~18 of the 30 items feed these
#: four scores, which is correct rather than a defect: the RSQ embeds Collins &
#: Read AAS material that belongs to other subscales this product does not
#: compute.
_PROTOTYPES = {
    "secure": ([3, 10, 15], [9, 28]),
    # Item 26, not 28. The shipped version read `(6 - r[28])` here — the same
    # term, same sign, already in the secure scale directly above. Almost
    # certainly `26` typed as `28` with the reverse-keying copied along with
    # it. It matters: 26 ("I prefer not to depend on others") is a canonical
    # dismissing item, while 28 ("I worry about having others not accept me")
    # is a self-model anxiety item with no place in this scale. The error also
    # made the term cancel between secure and dismissing, so it had no power to
    # separate the two prototypes that most need separating.
    "dismissive-avoidant": ([2, 6, 19, 22, 26], []),
    "anxious-preoccupied": ([8, 16, 25], [6]),
    "fearful-avoidant": ([1, 5, 12, 24], []),
}


def calculate_rsq_attachment_style(rsq_responses):
    """``(style, scores)``. ``style`` is None when there is too little to say.

    Returning None rather than a label is the point of the second fix here. The
    previous version defaulted every missing item to 3, so a blank submission
    scored all four prototypes at exactly 3.0 and ``max()`` returned whichever
    key came first — labelling anyone who skipped as **securely attached**. That
    was invisible while the questionnaire was mandatory and becomes a live
    mislabelling the moment the onboarding gate is removed.

    None is chosen over the string "unknown" deliberately: every consumer
    already guards with a falsy check — ``(profile.attachment_style or "")`` in
    ``portrait.py`` and ``engagement/services.py``, ``if getattr(...)`` in
    ``chat/assist.py`` — so None does the right thing in all three with no
    change to any of them, while "unknown" would be truthy and would inject
    ``attachment style: unknown`` into a prompt.
    """
    r = {int(k): int(v) for k, v in rsq_responses.items() if str(k).isdigit()}
    answered = len(r)

    for i in range(1, 31):
        if i not in r:
            r[i] = 3

    scores = {}
    for style, (plain, reversed_items) in _PROTOTYPES.items():
        total = sum(r[i] for i in plain) + sum(6 - r[i] for i in reversed_items)
        scores[style] = total / float(len(plain) + len(reversed_items))

    if answered < MIN_ITEMS_TO_SCORE:
        return None, scores

    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    # A tie at the top is not a finding. It is what an undifferentiated set of
    # answers looks like, and picking one anyway is how "secure" used to happen.
    if len(ranked) > 1 and ranked[0][1] == ranked[1][1]:
        return None, scores

    return ranked[0][0], scores

def calculate_communication_style(quiz_responses):
    counts = {
        "assertive": 0,
        "passive": 0,
        "analytical": 0,
        "expressive": 0,
        "avoidant": 0
    }
    for q, ans in quiz_responses.items():
        if ans in counts:
            counts[ans] += 1
            
    priority = ["assertive", "analytical", "expressive", "avoidant", "passive"]
    max_count = -1
    selected_style = "assertive"
    for style in priority:
        if counts[style] > max_count:
            max_count = counts[style]
            selected_style = style
            
    return selected_style

def build_modifiers(profile):
    tone_map = {
        "assertive": "direct and peer-to-peer",
        "passive": "supportive with more scaffolding",
        "analytical": "evidence-based with psychoeducation",
        "expressive": "emotionally resonant with metaphors",
        "avoidant": "indirect with less confrontational prompting"
    }
    communication_tone = tone_map.get(profile.communication_style_self_report, "direct and peer-to-peer")
    
    if profile.family_community_orientation == "family-community":
        cultural_framing = "family and community wellbeing"
    else:
        cultural_framing = "individual wellbeing"
        
    if profile.religious_values:
        religious_context = f"draw on {profile.religious_values} when therapeutically appropriate (never use religious framing to discourage separation in unsafe situations)"
    else:
        religious_context = None
        
    stage_map = {
        "early_dating": "foundation skills and healthy boundaries",
        "committed": "conflict management and shared meaning",
        "post_infidelity": "Gottman Trust Revival Method, structured timeline",
        "separation_considering": "discernment counseling approach, both paths supported, no persuasion",
        "long_term": "rekindling intimacy and navigating transitions",
        "newlyweds": "establishing routines and shared values",
        "crisis": "de-escalation, emotional safety, and stability"
    }
    relationship_stage_focus = stage_map.get(profile.relationship_stage, "foundation skills and healthy boundaries")
    
    attachment_map = {
        "secure": "balanced prompting supporting both independence and intimacy",
        "anxious-preoccupied": "explicit reassurance and co-regulation techniques",
        "dismissive-avoidant": "more space and less emotionally intense prompting",
        "fearful-avoidant": "gentle pacing, safety building, and validation of conflicting feelings"
    }
    # No default. The old fallback was the *secure* adaptation — "balanced
    # prompting supporting both independence and intimacy" — so a profile with
    # no assessed style was silently coached as though it were secure. That is
    # the same mislabelling the scorer now refuses to make, reappearing one
    # layer down, and it would have undone the fix entirely.
    #
    # None means the prompt gets no attachment line at all, which is the honest
    # state: we do not know, so we do not adapt.
    attachment_adaptations = attachment_map.get(profile.attachment_style) or None

    return {
        "communication_tone": communication_tone,
        "cultural_framing": cultural_framing,
        "religious_context": religious_context,
        "relationship_stage_focus": relationship_stage_focus,
        "attachment_adaptations": attachment_adaptations
    }

@shared_task(name="personalization.tasks.compute_prompt_modifiers")
def compute_prompt_modifiers(user_profile_id):
    """Computes prompt modifiers asynchronously after questionnaire completion."""
    try:
        profile = UserProfile.objects.get(id=user_profile_id)
        logger.info(f"Computing prompt modifiers for user profile {user_profile_id}")
        
        if profile.rsq_responses:
            style, _ = calculate_rsq_attachment_style(profile.rsq_responses)
            # Same two rules as the serializer's synchronous path, which this
            # duplicates: the column is non-null so an indeterminate result is
            # stored as empty, and the source only claims the questionnaire
            # when the questionnaire actually produced something.
            profile.attachment_style = style or ''
            profile.attachment_style_source = 'rsq_onboarding' if style else ''
            if not profile.attachment_assessed_at:
                profile.attachment_assessed_at = timezone.now()
                
        if profile.communication_style_quiz_responses:
            comm_style = calculate_communication_style(profile.communication_style_quiz_responses)
            profile.communication_style_self_report = comm_style
            
        profile.prompt_modifiers = build_modifiers(profile)
        
        # Answered, not labelled — see the serializer for why these came
        # apart once the scorer learned to say "I cannot tell".
        if (profile.rsq_responses and profile.relationship_stage and
            profile.cultural_background and profile.communication_style_self_report):
            if not profile.onboarding_completed:
                profile.onboarding_completed = True
                profile.onboarding_completed_at = timezone.now()
                
        profile.save()
        logger.info(f"Successfully computed prompt modifiers for profile {user_profile_id}")
        
    except UserProfile.DoesNotExist:
        logger.error(f"UserProfile {user_profile_id} not found")


@shared_task(name="personalization.assess_ruptures")
def assess_ruptures(window_days: int | None = None) -> int:
    """Judge every unassessed exchange that might have been an argument.

    The lexicon finds candidates; something that can read the conversation
    decides. Runs here rather than anywhere near a send because the question is
    retrospective — Tuesday's argument is the same argument for ever — so each
    exchange is judged once, stored, and never reconsidered. That is what makes
    a model call affordable for something the connection score depends on, and
    what keeps the score deterministic when it is read.

    Both answers are stored. Recording "this was not a fight" is what stops the
    same benign exchange being re-judged every night for a fortnight.

    A failed call stores nothing, so the exchange is a candidate again tomorrow
    rather than being recorded as benign because the provider was down.
    """
    from datetime import timedelta

    from apps.chat.assist import assess_rupture
    from apps.chat.models import CoupleMessage
    from apps.personalization import connection
    from apps.personalization.models import RuptureAssessment
    from apps.relationships.models import Relationship

    since = timezone.now() - timedelta(days=window_days or connection.WINDOW_DAYS)
    assessed = 0

    for relationship in Relationship.objects.filter(status="active").iterator():
        try:
            rows = list(
                CoupleMessage.objects.filter(
                    relationship=relationship,
                    created_at__gte=since,
                    deleted_at__isnull=True,
                )
                .select_related("media")
                .order_by("created_at")
            )
            if not rows:
                continue

            already = set(
                RuptureAssessment.objects.filter(
                    relationship=relationship, started_at__gte=since
                ).values_list("started_at", flat=True)
            )

            for start, end, lines in connection.conversation_windows(relationship, rows):
                if start in already:
                    continue
                answer = assess_rupture(lines)
                if answer is None:
                    continue
                is_rupture, confidence = answer
                RuptureAssessment.objects.update_or_create(
                    relationship=relationship,
                    started_at=start,
                    defaults={
                        "ended_at": end,
                        "is_rupture": is_rupture,
                        "confidence": confidence,
                    },
                )
                assessed += 1
        except Exception:
            logger.warning(
                "rupture_assessment_failed relationship=%s",
                relationship.id,
                exc_info=True,
            )

    logger.info("ruptures_assessed count=%s", assessed)
    return assessed


@shared_task(name="personalization.refresh_connection_scores")
def refresh_connection_scores() -> int:
    """Recompute every active couple's connection score.

    Daily rather than on write. The score is a fortnight-wide measure smoothed
    over weeks — recomputing it on every message would be a great deal of work
    to produce the same number, and would put a query fan-out on the send path
    for something nobody is waiting on.
    """
    from apps.personalization import connection
    from apps.relationships.models import Relationship

    # Judge first, then score. The score reads stored assessments and calls
    # nothing itself, so an exchange nobody has assessed simply is not a
    # rupture — which is the safe direction, but also means the order here
    # matters: scoring before assessing would leave every couple a day behind.
    try:
        assess_ruptures()
    except Exception:
        logger.warning("rupture_assessment_sweep_failed", exc_info=True)

    updated = 0
    for relationship in Relationship.objects.filter(status="active").iterator():
        try:
            if connection.update(relationship) is not None:
                updated += 1
        except Exception:
            logger.warning(
                "connection_refresh_failed relationship=%s",
                relationship.id,
                exc_info=True,
            )
    logger.info("connection_scores_refreshed count=%s", updated)
    return updated
