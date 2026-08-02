import logging
from celery import shared_task
from django.utils import timezone
from apps.personalization.models import UserProfile

logger = logging.getLogger(__name__)

def calculate_rsq_attachment_style(rsq_responses):
    r = {int(k): int(v) for k, v in rsq_responses.items() if str(k).isdigit()}
    for i in range(1, 31):
        if i not in r:
            r[i] = 3
            
    secure_score = (r[3] + (6 - r[9]) + r[10] + r[15] + (6 - r[28])) / 5.0
    dismissing_score = (r[2] + r[6] + r[19] + r[22] + (6 - r[28])) / 5.0
    preoccupied_score = ((6 - r[6]) + r[8] + r[16] + r[25]) / 4.0
    fearful_score = (r[1] + r[5] + r[12] + r[24]) / 4.0
    
    scores = {
        "secure": secure_score,
        "dismissive-avoidant": dismissing_score,
        "anxious-preoccupied": preoccupied_score,
        "fearful-avoidant": fearful_score
    }
    assigned_style = max(scores, key=scores.get)
    return assigned_style, scores

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
    attachment_adaptations = attachment_map.get(profile.attachment_style, "balanced prompting supporting both independence and intimacy")
    
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
            profile.attachment_style = style
            profile.attachment_style_source = 'rsq_onboarding'
            if not profile.attachment_assessed_at:
                profile.attachment_assessed_at = timezone.now()
                
        if profile.communication_style_quiz_responses:
            comm_style = calculate_communication_style(profile.communication_style_quiz_responses)
            profile.communication_style_self_report = comm_style
            
        profile.prompt_modifiers = build_modifiers(profile)
        
        if (profile.attachment_style and profile.relationship_stage and 
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
