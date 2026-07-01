import logging
from apps.accounts.models import GuardianConsent

logger = logging.getLogger(__name__)

# REL-57 — Hardcoded safety logic for minor abuse disclosure
SAFEGUARDING_RESOURCES = {
    "hotline": "1-800-422-4453",
    "organization": "Childhelp National Child Abuse Hotline",
    "instructions": "If you are in immediate danger, please call 911 or your local emergency services."
}

ABUSE_KEYWORDS = [
    "hit me", "hurt me", "punched", "kicked", "scared of my dad", 
    "scared of my mom", "scared of my guardian", "abusing me",
    "touching me", "hurting me", "don't tell my parents"
]

def check_guardian_abuse_disclosure(user, session_text):
    """
    Hardcoded check for abuse disclosure by minor users.
    Per REL-57: This logic is non-configurable and must route to safeguarding.
    """
    if not user.is_minor:
        return None

    session_text_lower = session_text.lower()
    
    # 1. Check for abuse patterns
    is_abuse_detected = any(keyword in session_text_lower for keyword in ABUSE_KEYWORDS)
    
    if is_abuse_detected:
        # 2. Flag the guardian consent as potentially compromised
        # REL-57: Do NOT share session content with that guardian under any circumstances
        guardian_consents = GuardianConsent.objects.filter(user=user)
        for consent in guardian_consents:
            consent.abuse_disclosed = True
            consent.save()
            
        logger.warning(f"Abuse disclosure detected for minor user {user.id}. Guardian access revoked.")
        
        # 3. Return the safeguarding resources
        return {
            "status": "abuse_flagged",
            "resources": SAFEGUARDING_RESOURCES,
            "next_steps": "Immediate routing to safeguarding required."
        }
        
    return None
