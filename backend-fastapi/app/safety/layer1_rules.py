import re
from dataclasses import dataclass
from enum import Enum
import time

class SignalCategory(str, Enum):
    SUICIDAL_IDEATION = "suicidal_ideation"
    SELF_HARM = "self_harm"
    PHYSICAL_ABUSE = "physical_abuse"
    EMOTIONAL_ABUSE = "emotional_abuse"
    COERCIVE_CONTROL = "coercive_control"
    CRISIS = "crisis"
    PERPETRATOR_LANGUAGE = "perpetrator_language"
    MANIPULATION_ATTEMPT = "manipulation_attempt"
    SAFE = "safe"

@dataclass
class Layer1Result:
    score: float           # 0.0–1.0
    category: SignalCategory
    matched_patterns: list[str]
    latency_ms: float

# HIGH-CONFIDENCE PATTERNS (score: 0.9+)
HIGH_CONFIDENCE_PATTERNS = {
    SignalCategory.SUICIDAL_IDEATION: [
        r'\b(want to|going to|thinking about|considering)\s+(kill|end|take)\s+(my(self)?|it all)\b',
        r'\b(suicide|suicidal|kill myself|end my life|take my life)\b',
        r'\b(don\'?t want to (live|be alive|be here) anymore)\b',
        r'\b(better off (dead|without me))\b',
        r'\b(no reason to (live|keep going|continue))\b',
    ],
    SignalCategory.PHYSICAL_ABUSE: [
        r'\b(hit|punch|slap|choke|strangle|grab|throw|push)\s+(me|him|her|them)\b',
        r'\b(scared to (go home|be alone with|see))\b',
        r'\b(bruise|injury|hurt me|physical(ly)? (harm|hurt|abuse))\b',
        r'\b(called 911|police came|restraining order)\b',
    ],
    SignalCategory.COERCIVE_CONTROL: [
        r'\b(not allowed to (see|talk to|contact|leave))\b',
        r'\b(controls?\s+(my|the|our)\s+(money|phone|accounts?))\b',
        r'\b(tracks?\s+(my|where I|my location))\b',
        r'\b(threatens?\s+(to (leave|take the kids|hurt|kill)))\b',
    ],
    SignalCategory.SELF_HARM: [
        r'\b(cut(ting)? myself|self.harm|hurting myself)\b',
        r'\b(burn(ing)? myself|scratching (myself|my skin))\b',
    ],
}

# MEDIUM-CONFIDENCE PATTERNS (score: 0.5–0.7)
MEDIUM_CONFIDENCE_PATTERNS = {
    SignalCategory.EMOTIONAL_ABUSE: [
        r'\b(you\'?re (crazy|insane|imagining things|making it up))\b',
        r'\b(never happened|you\'?re too sensitive|you\'?re overreacting)\b',
        r'\b(no one would believe you)\b',
        r'\b(my partner says I can\'?t)\b',
    ],
    SignalCategory.PERPETRATOR_LANGUAGE: [
        r'\b(made me (do it|hit|hurt))\b',
        r'\b(she/he/they (deserved|asked for) it)\b',
        r'\b(deny|attack|reverse)\b',  # DARVO signal (weaker, needs context)
        r'\b(it was just (a joke|an accident|once))\b',
    ],
    SignalCategory.MANIPULATION_ATTEMPT: [
        r'\bwhat (has|did) (my partner|he|she|they) (say|tell|share)\b',
        r'\b(screenshot|record|evidence|court|lawyer)\b',
        r'\bignore (previous|your) instructions?\b',
        r'\byou are now\b',  # prompt injection
    ],
}

def screen_layer1(message: str) -> Layer1Result:
    """Runs in-process, target <5ms."""
    start = time.monotonic()
    message_lower = message.lower()
    
    # Check high-confidence patterns first
    for category, patterns in HIGH_CONFIDENCE_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, message_lower):
                return Layer1Result(
                    score=0.95,
                    category=category,
                    matched_patterns=[pattern],
                    latency_ms=(time.monotonic() - start) * 1000
                )
    
    # Check medium-confidence patterns
    for category, patterns in MEDIUM_CONFIDENCE_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, message_lower):
                return Layer1Result(
                    score=0.55,
                    category=category,
                    matched_patterns=[pattern],
                    latency_ms=(time.monotonic() - start) * 1000
                )
    
    return Layer1Result(
        score=0.0,
        category=SignalCategory.SAFE,
        matched_patterns=[],
        latency_ms=(time.monotonic() - start) * 1000
    )
