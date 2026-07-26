"""Unit tests for app/orchestration/tone_coach.py internals (no HTTP)."""

import pytest

from app.orchestration import tone_coach as tc


def test_extract_json_plain():
    assert tc._extract_json('{"a": 1}') == {"a": 1}


def test_extract_json_with_code_fence_and_prose():
    raw = 'Sure! ```json\n{"mood": "tired"}\n``` hope that helps'
    assert tc._extract_json(raw) == {"mood": "tired"}


def test_extract_json_returns_none_on_junk():
    assert tc._extract_json("not json at all") is None
    assert tc._extract_json("") is None


def test_extract_json_ignores_non_dict():
    assert tc._extract_json("[1, 2, 3]") is None


def test_norm_intensity():
    assert tc._norm_intensity("HIGH") == "high"
    assert tc._norm_intensity("wat") == "medium"
    assert tc._norm_intensity(None) == "medium"


@pytest.mark.asyncio
async def test_analyze_mood_empty_returns_fallback():
    result = await tc.analyze_mood("   ")
    assert result["mood"] == "unclear"
    assert "check in" in result["disclaimer"].lower()


@pytest.mark.asyncio
async def test_analyze_mood_always_has_required_keys():
    result = await tc.analyze_mood("I'm feeling good today")
    for key in ("mood", "intensity", "summary", "suggestion", "disclaimer"):
        assert key in result and result[key]


@pytest.mark.asyncio
async def test_coach_reply_declines_perpetrator_language():
    result = await tc.coach_reply("She deserved it, she made me do it.")
    assert result["rewrites"] == []
    assert result["safety"] and result["safety"]["reason"] == "harm_signals"


@pytest.mark.asyncio
async def test_coach_reply_ordinary_draft_is_coachable():
    result = await tc.coach_reply("I felt hurt when you were late.")
    assert result["safety"] is None
    assert "disclaimer" in result


@pytest.mark.asyncio
async def test_suggest_replies_empty_input():
    assert await tc.suggest_replies([]) == []
    assert await tc.suggest_replies([{"role": "me", "content": "  "}]) == []
