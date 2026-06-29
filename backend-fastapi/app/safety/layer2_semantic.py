from dataclasses import dataclass
from app.safety.layer1_rules import SignalCategory

@dataclass
class Layer2Result:
    score: float
    category: SignalCategory
    similarity: float

async def screen_layer2(message: str, threshold: float = 0.85) -> Layer2Result:
    """
    Mock of pgvector cosine similarity search.
    If the message is semantically related to crisis, we return a score.
    """
    msg_lower = message.lower()
    
    # Paraphrased checks to simulate vector similarity
    if "end my life" in msg_lower or "kill myself" in msg_lower or "die" in msg_lower:
        return Layer2Result(score=0.9, category=SignalCategory.SUICIDAL_IDEATION, similarity=0.92)
        
    if "hurt me" in msg_lower or "abused me" in msg_lower or "violence" in msg_lower:
        return Layer2Result(score=0.95, category=SignalCategory.PHYSICAL_ABUSE, similarity=0.94)

    return Layer2Result(score=0.0, category=SignalCategory.SAFE, similarity=0.0)
