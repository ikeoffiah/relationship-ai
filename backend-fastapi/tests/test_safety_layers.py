import pytest
import time
from app.safety.layer1_rules import screen_layer1, SignalCategory
from app.safety.layer2_semantic import screen_layer2
from app.safety.layer3_contextual import screen_layer3
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
