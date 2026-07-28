"""Tests for the provider-agnostic LLM layer and the counseling system prompt."""

import os

import pytest

from app.orchestration import llm_provider
from app.orchestration.graph import build_system_prompt
import types
from app.orchestration.model_config import MODEL_CONFIG


@pytest.mark.asyncio
async def test_falls_back_to_safe_reply_when_provider_disabled(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "none")
    reply = await llm_provider.generate_reply("sys", [{"role": "user", "content": "hi"}])
    assert reply == llm_provider.FALLBACK_REPLY


@pytest.mark.asyncio
async def test_openai_without_key_falls_back(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    reply = await llm_provider.generate_reply("sys", [{"role": "user", "content": "hi"}])
    assert reply == llm_provider.FALLBACK_REPLY
    assert reply.strip()  # never empty


@pytest.mark.asyncio
async def test_provider_error_degrades_gracefully(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-invalid")

    async def _boom(*a, **k):
        raise RuntimeError("provider down")

    monkeypatch.setattr(llm_provider, "_openai", _boom)
    reply = await llm_provider.generate_reply("sys", [{"role": "user", "content": "hi"}])
    assert reply == llm_provider.FALLBACK_REPLY


def test_provider_is_switchable_by_env(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    assert llm_provider._provider() == "anthropic"
    monkeypatch.setenv("LLM_PROVIDER", "OpenAI")
    assert llm_provider._provider() == "openai"
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    assert llm_provider._provider() == "openai"  # default


def test_system_prompt_personalizes_by_attachment_style():
    prompt = build_system_prompt(
        strategy={"primary": "Validation", "secondary": "Exploration", "focus": "current emotion"},
        modifiers={"attachment_style": "anxious-preoccupied", "communication_style": "expressive"},
        safety_state={"level": "safe"},
        disclosures=[],
    )
    assert "counselor" in prompt.lower()
    assert "reassurance" in prompt.lower()  # anxious-style guidance woven in
    assert "expressive" in prompt.lower()


def test_system_prompt_neutral_without_profile():
    prompt = build_system_prompt(
        strategy={"primary": "Validation", "focus": "current emotion"},
        modifiers={},
        safety_state={"level": "safe"},
        disclosures=[],
    )
    assert "counselor" in prompt.lower()
    assert "reassurance" not in prompt.lower()


def test_system_prompt_flags_elevated_distress():
    prompt = build_system_prompt(
        strategy={},
        modifiers={},
        safety_state={"level": "elevated"},
        disclosures=[],
    )
    assert "emotional safety" in prompt.lower()


@pytest.mark.asyncio
async def test_generate_reply_ignores_empty_messages(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "none")
    reply = await llm_provider.generate_reply("sys", [{"role": "user", "content": ""}])
    assert reply == llm_provider.FALLBACK_REPLY


# Keep the environment clean for other test modules.
@pytest.fixture(autouse=True)
def _restore_env():
    saved = {k: os.environ.get(k) for k in ("LLM_PROVIDER", "OPENAI_API_KEY", "ANTHROPIC_API_KEY")}
    yield
    for k, v in saved.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v


def test_system_prompt_includes_memories():
    from app.orchestration.graph import build_system_prompt

    prompt = build_system_prompt(
        strategy={},
        modifiers={},
        safety_state={"level": "safe"},
        disclosures=[],
        memories=[{"memory_type": "trigger", "note": "feels dismissed when interrupted"}],
    )
    assert "past sessions" in prompt.lower()
    assert "feels dismissed when interrupted" in prompt


def test_system_prompt_no_memory_section_when_empty():
    from app.orchestration.graph import build_system_prompt

    prompt = build_system_prompt(
        strategy={}, modifiers={}, safety_state={"level": "safe"}, disclosures=[], memories=[]
    )
    assert "past sessions" not in prompt.lower()


@pytest.mark.asyncio
async def test_fetch_memories_graceful_without_config(monkeypatch):
    from app.api.chat_router import fetch_memories

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert await fetch_memories("user-1", "I feel overwhelmed") == []


@pytest.mark.asyncio
async def test_node_3_passes_memories_through():
    from app.orchestration.graph import node_3_memory_retrieval
    from app.orchestration.state import (
        AccessPolicy,
        SafetyState,
        SessionState,
        StrategyMix,
    )

    state = SessionState(
        session_id="s", user_id="u", relationship_id=None, session_type="individual",
        access_policy=AccessPolicy(can_read_private=True, can_read_shared=False, can_cross_partner=False),
        current_strategy=StrategyMix(primary="", secondary="", focus=""),
        safety_state=SafetyState(level="safe", score=0.0), turn_number=1,
        short_term_buffer=[{"role": "user", "content": "hi", "timestamp": ""}],
        retrieved_memories=[{"memory_type": "trigger", "note": "prefers space when upset"}],
        signal_vector=None, personalization_modifiers={}, is_streaming=False,
    )
    result = await node_3_memory_retrieval(state)
    assert result["retrieved_memories"][0]["note"] == "prefers space when upset"


# ── Fast lane ───────────────────────────────────────────────────────────────
# Inline assists (rephrase, mood read, suggestions) run while the user is still
# typing, so they must not pay the counseling model's latency. Measured p50 was
# 2.05s on the old shared default vs 0.86s on the fast model.

@pytest.mark.asyncio
async def test_fast_calls_use_the_low_latency_model(monkeypatch):
    seen = {}

    class _FakeCompletions:
        async def create(self, **kwargs):
            seen.update(kwargs)
            msg = types.SimpleNamespace(content="ok")
            return types.SimpleNamespace(choices=[types.SimpleNamespace(message=msg)])

    class _FakeClient:
        def __init__(self, **_):
            self.chat = types.SimpleNamespace(completions=_FakeCompletions())

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.delenv("OPENAI_FAST_MODEL", raising=False)
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    import openai
    monkeypatch.setattr(openai, "AsyncOpenAI", _FakeClient, raising=False)

    await llm_provider.generate_reply("sys", [{"role": "user", "content": "hi"}], fast=True)
    assert seen["model"] == MODEL_CONFIG["fast_path"]["model_id"]
    assert seen["max_tokens"] == llm_provider.MAX_FAST_TOKENS

    seen.clear()
    await llm_provider.generate_reply("sys", [{"role": "user", "content": "hi"}])
    assert seen["model"] == MODEL_CONFIG["primary_counseling"]["model_id"]
    assert seen["max_tokens"] == llm_provider.MAX_REPLY_TOKENS


def test_fast_path_model_is_not_a_reasoning_model():
    """gpt-5* reasoning models spend the token budget thinking and can return
    an empty string — unusable for an inline assist."""
    assert not MODEL_CONFIG["fast_path"]["model_id"].startswith("gpt-5")
