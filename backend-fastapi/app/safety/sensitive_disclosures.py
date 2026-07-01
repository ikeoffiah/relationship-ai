import re
from enum import Enum
from typing import Optional, List

SUSPENDED_JOINT_SESSIONS = set()


class DisclosureType(str, Enum):
    INFIDELITY = "infidelity"
    LEGAL = "legal"
    MANIPULATION = "manipulation"
    MUTUAL_ABUSE = "mutual_abuse"

INFIDELITY_SIGNALS = [
    "cheating", "affair", "seeing someone else", "slept with", "been with someone",
    "cheated on", "i kissed", "i've been seeing", "i had sex with", "one-night stand"
]


LEGAL_SIGNALS = [
    "divorce lawyer", "custody case", "evidence", "court", "legal proceedings",
    "my attorney", "screenshot this", "record this conversation", "print this out for"
]

MANIPULATION_PATTERNS = [
    r"what (has|did) (my partner|he|she|they) (say|tell|share)",
    r"what does (my partner|he|she|they) think (of|about) me",
    r"has (my partner|he|she|they) (mentioned|talked about) me",
    r"(can you|could you|please) (confirm|verify|tell me if)",
    r"I need (proof|evidence|confirmation)",
    r"(help me|tell me how to) (convince|manipulate|get) (him|her|them|my partner)",
    r"how (can I|do I|should I) (win|beat|get back at)",
]

LEGAL_REFUSAL_RESPONSE = """
Session transcripts and AI-generated content from RelationshipAI are not 
designed or intended for use as legal documentation. I can't produce output 
intended for legal proceedings. What I can do is support you in processing 
what you're going through. Would that be helpful?
""".strip()

MANIPULATION_REFUSAL = """
I'm designed to support each person individually, not to share information 
between partners without consent. I can't answer questions about what your 
partner has shared or thought. What I can do is help you work through your 
own experience.
""".strip()

BOTH_PARTNERS_ABUSE_RESPONSE = """
What you're describing is serious, and I want to make sure you're supported. 
I'm going to suggest connecting with a specialist who can help navigate this 
more effectively than I can. [Crisis/specialist resources]
""".strip()

INFIDELITY_HANDLING_PROMPT = """
The user has disclosed infidelity. Your role is to support them in processing this — not to judge or advise on whether to disclose. If they ask for help crafting deceptive communications, decline and offer instead to help them prepare for an honest conversation.
""".strip()

NARRATIVE_EPISTEMIC_PROMPT = """
Frame all partner-report statements with epistemic markers (e.g., "Partner A has shared their experience that..."). Do NOT adjudicate which account is true or ask who is right.
""".strip()

class SensitiveDisclosureDetector:
    @staticmethod
    def detect(message: str, session_type: str, other_partner_claims_abuse: bool = False) -> Optional[DisclosureType]:
        text_lower = message.lower()
        
        # Check for abuse claim first
        is_abuse_claim = "abuse" in text_lower or "abusive" in text_lower or "violence" in text_lower
        if is_abuse_claim and other_partner_claims_abuse:
            return DisclosureType.MUTUAL_ABUSE
            
        # Check manipulation patterns
        for pattern in MANIPULATION_PATTERNS:
            if re.search(pattern, text_lower):
                return DisclosureType.MANIPULATION
                
        # Check legal signals
        for signal in LEGAL_SIGNALS:
            if signal in text_lower:
                return DisclosureType.LEGAL
                
        # Check infidelity signals
        for signal in INFIDELITY_SIGNALS:
            if signal in text_lower:
                return DisclosureType.INFIDELITY
                
        return None


class NarrativeEpistemicWrapper:
    @staticmethod
    def wrap_partner_statement(statement: str, partner_label: str) -> str:
        """Wraps any statement sourced from the other partner with epistemic framing."""
        return f"{partner_label} has shared their experience that {statement.lower()}"

def get_sensitive_disclosure_injections(active_disclosures: List[str]) -> List[str]:
    injections = []
    if DisclosureType.INFIDELITY.value in active_disclosures:
        injections.append(INFIDELITY_HANDLING_PROMPT)
    if "conflicting_narrative" in active_disclosures:
        injections.append(NARRATIVE_EPISTEMIC_PROMPT)
    return injections
