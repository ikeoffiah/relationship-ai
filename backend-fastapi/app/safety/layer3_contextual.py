from dataclasses import dataclass
from app.safety.layer1_rules import SignalCategory

@dataclass
class Layer3Result:
    score: float
    category: SignalCategory
    reason: str

async def screen_layer3(message: str, session_context: list) -> Layer3Result:
    """
    Mock of contextual Claude Haiku check.
    Triggered when Layer 1 score is in [0.3, 0.7].
    """
    msg_lower = message.lower()
    
    if "suicide" in msg_lower or "kill" in msg_lower:
        return Layer3Result(score=0.9, category=SignalCategory.SUICIDAL_IDEATION, reason="Context indicates self-harm risk")
        
    if "hit" in msg_lower or "abuse" in msg_lower:
        return Layer3Result(score=0.9, category=SignalCategory.PHYSICAL_ABUSE, reason="Context indicates domestic violence risk")
        
    return Layer3Result(score=0.0, category=SignalCategory.SAFE, reason="No risk detected")
