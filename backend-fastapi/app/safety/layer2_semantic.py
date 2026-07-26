"""
Layer 2 — semantic safety screen.

Embeds the message and compares it (cosine similarity) to a bank of crisis
exemplar phrases, catching paraphrases the Layer-1 regex rules miss. Runs only
on messages Layer 1 already flagged as ambiguous, so a moderately sensitive
threshold is appropriate (a false positive just surfaces safety resources; a
false negative misses a crisis).

Degrades to the original keyword heuristic when embeddings are unavailable
(no OPENAI_API_KEY, or any error), so this layer is never *less* safe than the
mock it replaces. Thresholds and exemplars want calibration against a labeled
set — see docs/safety/classifier-upgrade.md.
"""

import math
import os
from dataclasses import dataclass

from app.safety.layer1_rules import SignalCategory

# Only runs on already-suspicious messages, so lean sensitive.
DEFAULT_THRESHOLD = 0.6

CRISIS_EXEMPLARS = {
    SignalCategory.SUICIDAL_IDEATION: [
        "I want to end my life",
        "I'm going to kill myself",
        "I don't want to be here anymore",
        "there's no point in going on",
        "everyone would be better off without me",
    ],
    SignalCategory.SELF_HARM: [
        "I want to hurt myself",
        "I've been cutting myself",
        "I deserve to be in pain",
    ],
    SignalCategory.PHYSICAL_ABUSE: [
        "my partner hit me",
        "they hurt me physically",
        "I'm scared they'll hurt me again",
    ],
    SignalCategory.COERCIVE_CONTROL: [
        "they control everything I do",
        "I'm not allowed to see my friends or family",
        "they track everywhere I go",
    ],
}

# Retained keyword fallback (the previous behavior) — used whenever embeddings
# aren't available, so we never regress below the mock.
_KEYWORD_FALLBACK = [
    (("end my life", "kill myself", "die"), SignalCategory.SUICIDAL_IDEATION, 0.9, 0.92),
    (("hurt me", "abused me", "violence"), SignalCategory.PHYSICAL_ABUSE, 0.95, 0.94),
]


@dataclass
class Layer2Result:
    score: float
    category: SignalCategory
    similarity: float


_exemplar_cache: list | None = None  # [(category, embedding), ...]


def _cosine(a, b) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


async def _embed(texts: list[str]) -> list[list[float]]:
    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=os.environ["OPENAI_API_KEY"])
    model = os.environ.get("EMBEDDING_MODEL", "text-embedding-3-small")
    resp = await client.embeddings.create(input=texts, model=model)
    return [d.embedding for d in resp.data]


def _keyword_screen(message: str) -> Layer2Result:
    ml = message.lower()
    for keywords, category, score, similarity in _KEYWORD_FALLBACK:
        if any(k in ml for k in keywords):
            return Layer2Result(score=score, category=category, similarity=similarity)
    return Layer2Result(score=0.0, category=SignalCategory.SAFE, similarity=0.0)


async def screen_layer2(message: str, threshold: float = DEFAULT_THRESHOLD) -> Layer2Result:
    if not os.environ.get("OPENAI_API_KEY"):
        return _keyword_screen(message)
    try:
        global _exemplar_cache
        if _exemplar_cache is None:
            flat = [(cat, p) for cat, ps in CRISIS_EXEMPLARS.items() for p in ps]
            embeddings = await _embed([p for _, p in flat])
            _exemplar_cache = list(zip([c for c, _ in flat], embeddings))

        (message_embedding,) = await _embed([message])
        best_category, best_similarity = SignalCategory.SAFE, 0.0
        for category, embedding in _exemplar_cache:
            similarity = _cosine(message_embedding, embedding)
            if similarity > best_similarity:
                best_similarity, best_category = similarity, category

        if best_similarity >= threshold:
            return Layer2Result(
                score=min(0.99, best_similarity),
                category=best_category,
                similarity=best_similarity,
            )
        # Below the semantic threshold — fall back to the keyword floor.
        return _keyword_screen(message)
    except Exception:
        return _keyword_screen(message)
