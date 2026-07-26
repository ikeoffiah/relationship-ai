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


# ── daily vibe heuristic (deterministic fallback, no keys) ────────────────

def test_heuristic_vibe_quiet_when_few_messages():
    label, _emoji, _blurb = tc._heuristic_vibe("hey there", count=2)
    assert label == "Quiet"


def test_heuristic_vibe_reconnecting_beats_tense():
    # "sorry" should read as repair even alongside conflict words.
    label, _, _ = tc._heuristic_vibe("i was upset but i'm sorry, let's make up", count=6)
    assert label == "Reconnecting"


def test_heuristic_vibe_playful():
    label, _, _ = tc._heuristic_vibe("haha lol that's so funny 😂 stop", count=5)
    assert label == "Playful"


def test_heuristic_vibe_logistical():
    label, _, _ = tc._heuristic_vibe("remind me to pay the bill and book the appointment", count=5)
    assert label == "Logistical"


def test_heuristic_vibe_defaults_to_everyday():
    label, _, _ = tc._heuristic_vibe("we talked about the weather and the garden", count=6)
    assert label == "Everyday"


@pytest.mark.asyncio
async def test_daily_vibe_always_returns_full_shape():
    result = await tc.daily_vibe([
        {"role": "me", "content": "love you so much ❤️"},
        {"role": "partner", "content": "miss you my love"},
        {"role": "me", "content": "call me tonight?"},
        {"role": "partner", "content": "of course babe"},
    ])
    for key in ("label", "emoji", "blurb", "disclaimer"):
        assert result[key]
    assert result["label"] in {label for label, _, _ in tc.VIBES}


@pytest.mark.asyncio
async def test_daily_vibe_empty_is_quiet():
    result = await tc.daily_vibe([])
    assert result["label"] == "Quiet"
