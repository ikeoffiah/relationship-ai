from django.db import models
from django.conf import settings

class UserProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="personalization_profile"
    )
    
    # Onboarding completion status
    onboarding_completed = models.BooleanField(default=False)
    onboarding_completed_at = models.DateTimeField(null=True, blank=True)
    
    # Screen 1 - Attachment Style (RSQ)
    rsq_responses = models.JSONField(default=dict, blank=True)
    attachment_style = models.CharField(max_length=50, blank=True)
    attachment_style_source = models.CharField(max_length=50, blank=True)
    attachment_assessed_at = models.DateTimeField(null=True, blank=True)
    
    # Screen 2 - Relationship Context
    relationship_stage = models.CharField(max_length=50, blank=True)
    relationship_duration_months = models.IntegerField(null=True, blank=True)
    cohabiting = models.BooleanField(null=True, blank=True)
    children_count = models.IntegerField(default=0)
    reason_for_using = models.CharField(max_length=200, blank=True)
    
    # Screen 3 - Cultural & Values Context
    cultural_background = models.CharField(max_length=255, blank=True)
    religious_values = models.CharField(max_length=255, blank=True)
    communication_style_preference = models.CharField(max_length=50, blank=True)  # direct / indirect
    family_community_orientation = models.CharField(max_length=50, blank=True)  # individual / family-community
    
    # Screen 4 - Communication Style Self-Report Quiz
    communication_style_quiz_responses = models.JSONField(default=dict, blank=True)
    communication_style_self_report = models.CharField(max_length=50, blank=True)  # assertive | passive | analytical | expressive | avoidant
    
    # Derived prompt modifiers
    prompt_modifiers = models.JSONField(default=dict, blank=True)
    
    class Meta:
        db_table = "personalization_profiles"
        
    def __str__(self):
        return f"Personalization Profile for {self.user.email}"


class BehaviourProfile(models.Model):
    """Observed tendencies, kept beside the self-report rather than over it.

    One row per user, holding ``{signal: {score, count, updated_at}}``. A JSON
    blob rather than a table of observations on purpose: we never need to query
    an individual observation, only the running total, and keeping one row per
    person means this cannot grow into a per-message log of someone's
    behaviour — which is a thing that would then exist, and be subpoenable, and
    be a much larger promise to keep than the feature is worth.

    Decay is applied on read and on write (see behaviour.py), so the stored
    score is always "as of updated_at" and never needs a sweep job.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="behaviour_profile",
    )
    signals = models.JSONField(default=dict, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "behaviour_profiles"

    def __str__(self):
        return f"Behaviour profile for {self.user_id}"
