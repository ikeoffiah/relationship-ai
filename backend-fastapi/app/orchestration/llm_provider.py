"""
Provider-agnostic LLM access for counseling generation.

The counseling reply is produced by whichever provider ``LLM_PROVIDER`` selects
— OpenAI by default (Anthropic also supported). Providers are imported lazily so
a missing SDK never breaks module import, and *every* failure path degrades to a
safe, non-empty holding reply: a counseling turn must never hand an empty string
to someone who may be in distress.

Switch providers with environment variables, no code change:

    LLM_PROVIDER   openai | anthropic | none        (default: openai)
    OpenAI         OPENAI_API_KEY, OPENAI_MODEL       (counseling; default gpt-4o)
                   OPENAI_FAST_MODEL                  (inline assists; default gpt-4.1-nano)
    Anthropic      ANTHROPIC_API_KEY, ANTHROPIC_MODEL (default: claude-sonnet-4-6)

Both providers take the same call shape here — a system prompt plus a list of
{"role": "user"|"assistant", "content": str} messages — so the rest of the
orchestration graph is provider-neutral.
"""

import os
from typing import Dict, List, Optional

from app.orchestration.model_config import MODEL_CONFIG

# Deliberately warm and non-committal: shown only when the real model is
# unavailable (no key, unreachable, or an error). Never a diagnosis or advice.
FALLBACK_REPLY = (
    "I'm here with you. I'm having trouble putting a full response together right "
    "now — can you tell me a little more about what's on your mind?"
)

MAX_REPLY_TOKENS = 1024

# Inline assists (rephrase, mood read, suggestions) answer briefly.
MAX_FAST_TOKENS = 320


def _provider() -> str:
    return os.environ.get("LLM_PROVIDER", "openai").strip().lower()


async def generate_reply(
    system_prompt: str,
    messages: List[Dict[str, str]],
    *,
    fast: bool = False,
) -> str:
    """Generate a reply from the configured provider.

    Set ``fast=True`` for anything that runs while the user is mid-sentence —
    rephrasing a message, reading a thread's mood, drafting suggestions. Those
    take the low-latency model instead of the counseling one, which is roughly
    2.4x quicker (see ``model_config``). Everything else gets the stronger
    model, because a considered reply is worth the extra second.

    Returns a non-empty string always: the provider's output, or ``FALLBACK_REPLY``
    if the provider is unset/unavailable or the call fails.
    """
    provider = _provider()
    try:
        if provider == "openai":
            return await _openai(system_prompt, messages, fast=fast) or FALLBACK_REPLY
        if provider == "anthropic":
            return await _anthropic(system_prompt, messages) or FALLBACK_REPLY
    except Exception:
        # Any provider error (auth, rate limit, network, SDK mismatch) degrades
        # to the holding reply rather than surfacing a stack trace mid-session.
        return FALLBACK_REPLY
    return FALLBACK_REPLY


def _clean(messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
    return [
        {"role": m.get("role", "user"), "content": m["content"]}
        for m in messages
        if m.get("content")
    ]


async def _openai(
    system_prompt: str,
    messages: List[Dict[str, str]],
    *,
    fast: bool = False,
) -> Optional[str]:
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        return None
    from openai import AsyncOpenAI  # lazy: absent SDK shouldn't break import

    client = AsyncOpenAI(api_key=key)
    if fast:
        model = os.environ.get(
            "OPENAI_FAST_MODEL", MODEL_CONFIG["fast_path"]["model_id"]
        )
        # Inline assists answer in a sentence or two; a smaller ceiling keeps a
        # runaway generation from stalling the compose box.
        max_tokens = MAX_FAST_TOKENS
    else:
        model = os.environ.get(
            "OPENAI_MODEL", MODEL_CONFIG["primary_counseling"]["model_id"]
        )
        max_tokens = MAX_REPLY_TOKENS
    convo = [{"role": "system", "content": system_prompt}, *_clean(messages)]
    resp = await client.chat.completions.create(
        model=model, max_tokens=max_tokens, messages=convo
    )
    return (resp.choices[0].message.content or "").strip()


async def _anthropic(system_prompt: str, messages: List[Dict[str, str]]) -> Optional[str]:
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return None
    from anthropic import AsyncAnthropic

    client = AsyncAnthropic(api_key=key)
    model = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6")
    resp = await client.messages.create(
        model=model,
        max_tokens=MAX_REPLY_TOKENS,
        system=system_prompt,
        messages=_clean(messages),
    )
    return "".join(getattr(b, "text", "") for b in resp.content).strip()
