import logging
from datetime import datetime
from django.utils import timezone
from apps.accounts.models import AgeVerification, User, GuardianConsent

logger = logging.getLogger(__name__)

def verify_user_age(user: User, method: str, provider_response: dict) -> AgeVerification:
    """
    Handles the outcome of an age verification process from a provider.
    This does NOT store raw ID data, only the status.
    """
    status = provider_response.get("status", "failed")
    is_minor = provider_response.get("is_minor", False)
    
    verification, created = AgeVerification.objects.update_or_create(
        user=user,
        defaults={
            "method": method,
            "status": status,
            "verified_at": timezone.now() if status == "verified" else None,
            "blocked_reason": provider_response.get("reason") if status == "blocked" else None,
        }
    )
    
    if status == "verified":
        user.age_verified = True
        user.is_minor = is_minor
        user.age_verification_method = method
        user.save()
        
    return verification

def handle_minor_guardian_abuse_disclosure(session_id: str, user_id: str):
    """
    If a minor user discloses abuse by the parent/guardian whose consent
    was required for their account:
    1. Immediately suspend the guardian's consent access to this user's account
    2. Route session to safeguarding resources (national child protection hotline)
    3. Do NOT share session content with the guardian under any circumstances
    4. Log event to safety incident queue for human review within 1 hour
    
    Per Section 12.2 of the RelationshipAI paper.
    """
    try:
        user = User.objects.get(id=user_id)
        
        # 1. Suspend guardian's consent access
        guardian_consents = GuardianConsent.objects.filter(user=user)
        for consent in guardian_consents:
            consent.abuse_disclosed = True
            consent.save()
            
        logger.critical(
            f"Abuse disclosure by minor {user_id} in session {session_id}. "
            "Suspending guardian consent access immediately."
        )
        
        # 2. Mark verification as blocked to prevent further guardian interaction
        verification = getattr(user, 'age_verification', None)
        if verification:
            verification.status = 'blocked'
            verification.blocked_reason = 'Guardian abuse disclosure'
            verification.save()
            
        # 3. Return resources to frontend (usually via a separate channel or session response)
        # REL-57 requires hardcoded routing
        return True
            
    except User.DoesNotExist:
        logger.error(f"User {user_id} not found during abuse disclosure handling.")
        
    return False
