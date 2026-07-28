import pytest
import time
from app.safety.layer1_rules import screen_layer1, SignalCategory
from app.safety.layer2_semantic import screen_layer2
from app.orchestration.graph import SafetyPreScreener

def test_layer1_rules():
    # Suicidal Ideation (High confidence)
    res_suicide = screen_layer1("I want to kill myself")
    assert res_suicide.score >= 0.9
    assert res_suicide.category == SignalCategory.SUICIDAL_IDEATION
    
    # Coercive control (High confidence)
    res_coercive = screen_layer1("he controls my money and tracks my location")
    assert res_coercive.score >= 0.9
    assert res_coercive.category == SignalCategory.COERCIVE_CONTROL
    
    # Emotional abuse (Medium confidence)
    res_emotional = screen_layer1("you're overreacting and crazy")
    assert 0.5 <= res_emotional.score < 0.8
    assert res_emotional.category == SignalCategory.EMOTIONAL_ABUSE
    
    # Safe message
    res_safe = screen_layer1("I love cooking dinner together.")
    assert res_safe.score == 0.0
    assert res_safe.category == SignalCategory.SAFE

def test_layer1_latency_benchmark():
    # Benchmark on a long-ish message
    long_msg = "I love cooking dinner together. " * 50
    
    start = time.perf_counter()
    for _ in range(100):
        screen_layer1(long_msg)
    avg_latency = (time.perf_counter() - start) * 1000 / 100
    
    assert avg_latency < 10.0  # Must run in <10ms

@pytest.mark.asyncio
async def test_layer2_paraphrases():
    res = await screen_layer2("I want to end my life")
    assert res.score >= 0.9
    assert res.category == SignalCategory.SUICIDAL_IDEATION

@pytest.mark.asyncio
async def test_safety_prescreener_pipeline():
    # 1. Critical message (L1 triggers immediately)
    score = await SafetyPreScreener.screen("I want to kill myself", {})
    assert score >= 0.9
    
    # 2. Ambiguous message (e.g. L1 triggers medium confidence, then L2/L3 escalates it)
    # "screenshot" triggers manipulation (0.55 score in L1 rules)
    # L2/L3 check resolves the score
    score_ambiguous = await SafetyPreScreener.screen("he is crazy and I want to end my life", {})
    assert score_ambiguous >= 0.9


@pytest.mark.asyncio
async def test_layer2_keyword_fallback_without_embeddings(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    from app.safety.layer2_semantic import screen_layer2
    hit = await screen_layer2("I want to end my life")
    assert hit.score >= 0.9 and hit.category == SignalCategory.SUICIDAL_IDEATION
    safe = await screen_layer2("I love cooking dinner together")
    assert safe.category == SignalCategory.SAFE


@pytest.mark.asyncio
async def test_layer3_keyword_fallback_without_llm(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    from app.safety.layer3_contextual import screen_layer3
    hit = await screen_layer3("I keep thinking about suicide", [])
    assert hit.score >= 0.9 and hit.category == SignalCategory.SUICIDAL_IDEATION
    safe = await screen_layer3("we had a nice walk", [])
    assert safe.category == SignalCategory.SAFE


@pytest.mark.asyncio
async def test_layer3_uses_llm_when_configured(monkeypatch):
    """With a key set, Layer 3 calls the LLM; we stub it to verify parsing."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    import app.safety.layer3_contextual as l3

    class _Msg:
        content = '{"category": "coercive_control", "score": 0.82, "reason": "isolation"}'

    class _Choice:
        message = _Msg()

    class _Resp:
        choices = [_Choice()]

    class _Completions:
        async def create(self, **kw):
            return _Resp()

    class _Chat:
        completions = _Completions()

    class _FakeClient:
        def __init__(self, **kw):
            self.chat = _Chat()

    monkeypatch.setattr(l3, "AsyncOpenAI", _FakeClient, raising=False)
    # Patch the lazy import target too.
    import openai
    monkeypatch.setattr(openai, "AsyncOpenAI", _FakeClient, raising=False)

    res = await l3.screen_layer3("they won't let me see anyone", [])
    assert res.category == SignalCategory.COERCIVE_CONTROL
    assert res.score >= 0.8


# ── Phrasing coverage for suicidal ideation ─────────────────────────────────
# The high-confidence patterns originally listed only bare verb stems
# ("kill", "end", "take") and the contracted "don't", so the most natural
# phrasings of a disclosure — "thinking about killing myself", "ending my
# life", "I do not want to live anymore" — scored 0.00 and reached no
# intervention at all. Missing a real disclosure is the worst failure this
# system has, so these are pinned.



@pytest.mark.parametrize(
    "message",
    [
        "I have been thinking about killing myself.",
        "I am thinking about ending my life.",
        "I keep thinking about taking my life.",
        "I do not want to live anymore.",
        "I want to kill myself.",
        "I feel suicidal.",
        "I would be better off dead.",
    ],
)
def test_suicidal_phrasings_are_detected(message):
    result = screen_layer1(message)
    assert result.category == SignalCategory.SUICIDAL_IDEATION
    assert result.score >= 0.7, f"undetected disclosure: {message}"


@pytest.mark.parametrize(
    "message",
    [
        "We killed it at work today.",
        "I want to end this argument.",
        "That movie was to die for.",
        "I do not want to live in that city anymore.",
    ],
)
def test_benign_phrasings_stay_safe(message):
    """Broadening the patterns must not manufacture false crises."""
    assert screen_layer1(message).category == SignalCategory.SAFE
