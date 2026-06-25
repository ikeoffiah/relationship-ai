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
