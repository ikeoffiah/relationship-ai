"""Unit tests for app/memory/extractor.py (REL-89)."""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.memory.extractor import (
    CONFIDENCE_THRESHOLD,
    MemoryCandidate,
    MemoryExtractor,
)


def candidate_dict(**overrides):
    base = {
        "content": "User asks for reassurance when plans change unexpectedly.",
        "memory_type": "stated_need",
        "confidence": 0.9,
        "why_stored": "Explains what helps the user settle during disruption.",
        "session_evidence": "I just need to know we're still okay.",
    }
    base.update(overrides)
    return base


def make_client(text):
    """Anthropic client double whose messages.create returns `text`."""
    client = MagicMock()
    response = MagicMock()
    response.content = [MagicMock(text=text)]
    client.messages = MagicMock()
    client.messages.create = AsyncMock(return_value=response)
    return client


@pytest.fixture
def messages():
    return [
        {"role": "user", "content": "We argued about the holidays again."},
        {"role": "assistant", "content": "What did that feel like?"},
    ]


# ---------------------------------------------------------------------------
# MemoryCandidate
# ---------------------------------------------------------------------------

def test_content_preview_truncates_to_50_chars():
    long_content = "a" * 120
    cand = MemoryCandidate(**candidate_dict(content=long_content))

    assert cand.content_preview == "a" * 50
    assert len(cand.content_preview) == 50


def test_content_preview_leaves_short_content_intact():
    cand = MemoryCandidate(**candidate_dict(content="short memory"))
    assert cand.content_preview == "short memory"


def test_confidence_outside_zero_to_one_is_rejected():
    with pytest.raises(Exception):
        MemoryCandidate(**candidate_dict(confidence=1.5))


def test_unknown_memory_type_is_rejected():
    with pytest.raises(Exception):
        MemoryCandidate(**candidate_dict(memory_type="astrology_sign"))


# ---------------------------------------------------------------------------
# _format_conversation
# ---------------------------------------------------------------------------

def test_format_conversation_uppercases_roles_and_joins_with_newlines():
    extractor = MemoryExtractor(anthropic_client=make_client("[]"))

    formatted = extractor._format_conversation(
        [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "hi there"},
        ]
    )

    assert formatted == "USER: hello\nASSISTANT: hi there"


def test_format_conversation_handles_missing_fields():
    extractor = MemoryExtractor(anthropic_client=make_client("[]"))

    formatted = extractor._format_conversation([{}, {"role": "user"}])

    assert formatted == "UNKNOWN: \nUSER: "


def test_format_conversation_of_empty_list_is_empty_string():
    extractor = MemoryExtractor(anthropic_client=make_client("[]"))
    assert extractor._format_conversation([]) == ""


# ---------------------------------------------------------------------------
# extract
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_empty_session_returns_empty_without_calling_api():
    client = make_client("[]")
    extractor = MemoryExtractor(anthropic_client=client)

    assert await extractor.extract(session_messages=[], user_id="u1") == []
    client.messages.create.assert_not_awaited()


@pytest.mark.asyncio
async def test_happy_path_parses_candidates(messages):
    payload = json.dumps(
        [
            candidate_dict(content="User softens when given time to think."),
            candidate_dict(content="Holidays are a recurring flashpoint.",
                           memory_type="conflict_pattern", confidence=0.82),
        ]
    )
    extractor = MemoryExtractor(anthropic_client=make_client(payload))

    results = await extractor.extract(session_messages=messages, user_id="u1")

    assert len(results) == 2
    assert all(isinstance(r, MemoryCandidate) for r in results)
    assert results[0].content == "User softens when given time to think."
    assert results[1].memory_type == "conflict_pattern"
    assert results[1].confidence == 0.82


@pytest.mark.asyncio
async def test_prompt_includes_the_formatted_conversation(messages):
    client = make_client("[]")
    extractor = MemoryExtractor(anthropic_client=client)

    await extractor.extract(session_messages=messages, user_id="u1")

    kwargs = client.messages.create.await_args.kwargs
    assert kwargs["model"] == "claude-haiku-4-5-20251001"
    assert kwargs["max_tokens"] == 2048
    prompt = kwargs["messages"][0]["content"]
    assert "USER: We argued about the holidays again." in prompt
    assert "ASSISTANT: What did that feel like?" in prompt


@pytest.mark.asyncio
async def test_low_confidence_candidates_are_dropped(messages):
    payload = json.dumps(
        [
            candidate_dict(content="kept", confidence=CONFIDENCE_THRESHOLD),
            candidate_dict(content="dropped", confidence=CONFIDENCE_THRESHOLD - 0.01),
            candidate_dict(content="also dropped", confidence=0.1),
        ]
    )
    extractor = MemoryExtractor(anthropic_client=make_client(payload))

    results = await extractor.extract(session_messages=messages, user_id="u1")

    assert [r.content for r in results] == ["kept"]


@pytest.mark.asyncio
async def test_malformed_json_returns_empty_list(messages):
    extractor = MemoryExtractor(anthropic_client=make_client("Sure! Here you go: {oops"))

    assert await extractor.extract(session_messages=messages, user_id="u1") == []


@pytest.mark.asyncio
async def test_json_code_fence_is_stripped(messages):
    payload = "```json\n" + json.dumps([candidate_dict(content="fenced")]) + "\n```"
    extractor = MemoryExtractor(anthropic_client=make_client(payload))

    results = await extractor.extract(session_messages=messages, user_id="u1")

    assert [r.content for r in results] == ["fenced"]


@pytest.mark.asyncio
async def test_bare_code_fence_is_stripped(messages):
    payload = "```\n" + json.dumps([candidate_dict(content="bare fence")]) + "\n```"
    extractor = MemoryExtractor(anthropic_client=make_client(payload))

    results = await extractor.extract(session_messages=messages, user_id="u1")

    assert [r.content for r in results] == ["bare fence"]


@pytest.mark.asyncio
async def test_surrounding_whitespace_is_tolerated(messages):
    payload = "\n\n  " + json.dumps([candidate_dict(content="padded")]) + "  \n"
    extractor = MemoryExtractor(anthropic_client=make_client(payload))

    results = await extractor.extract(session_messages=messages, user_id="u1")

    assert [r.content for r in results] == ["padded"]


@pytest.mark.asyncio
async def test_malformed_item_is_skipped_but_siblings_survive(messages):
    payload = json.dumps(
        [
            candidate_dict(content="good one"),
            {"content": "missing required fields"},
            {"not": "even close"},
            candidate_dict(content="good two", memory_type="trigger"),
        ]
    )
    extractor = MemoryExtractor(anthropic_client=make_client(payload))

    results = await extractor.extract(session_messages=messages, user_id="u1")

    assert [r.content for r in results] == ["good one", "good two"]


@pytest.mark.asyncio
async def test_invalid_memory_type_item_is_skipped(messages):
    payload = json.dumps(
        [
            candidate_dict(content="bogus type", memory_type="horoscope"),
            candidate_dict(content="valid"),
        ]
    )
    extractor = MemoryExtractor(anthropic_client=make_client(payload))

    results = await extractor.extract(session_messages=messages, user_id="u1")

    assert [r.content for r in results] == ["valid"]


@pytest.mark.asyncio
async def test_empty_json_array_returns_empty_list(messages):
    extractor = MemoryExtractor(anthropic_client=make_client("[]"))

    assert await extractor.extract(session_messages=messages, user_id="u1") == []


def test_extractor_pins_the_memory_extraction_model():
    extractor = MemoryExtractor(anthropic_client=make_client("[]"))
    assert extractor._model == "claude-haiku-4-5-20251001"
