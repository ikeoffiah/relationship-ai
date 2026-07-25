"""
Provider-agnostic LLM access for counseling generation.

The counseling reply is produced by whichever provider ``LLM_PROVIDER`` selects
— OpenAI by default (Anthropic also supported). Providers are imported lazily so
a missing SDK never breaks module import, and *every* failure path degrades to a
safe, non-empty holding reply: a counseling turn must never hand an empty string
to someone who may be in distress.

Switch providers with environment variables, no code change:

    LLM_PROVIDER   openai | anthropic | none        (default: openai)
    OpenAI         OPENAI_API_KEY, OPENAI_MODEL      (default model: gpt-4o)
    Anthropic      ANTHROPIC_API_KEY, ANTHROPIC_MODEL (default: claude-sonnet-4-6)

Both providers take the same call shape here — a system prompt plus a list of
{"role": "user"|"assistant", "content": str} messages — so the rest of the
orchestration graph is provider-neutral.
"""

import os
from typing import Dict, List, Optional

# Deliberately warm and non-committal: shown only when the real model is
# unavailable (no key, unreachable, or an error). Never a diagnosis or advice.
FALLBACK_REPLY = (
    "I'm here with you. I'm having trouble putting a full response together right "
    "now — can you tell me a little more about what's on your mind?"
)

MAX_REPLY_TOKENS = 1024


def _provider() -> str:
    return os.environ.get("LLM_PROVIDER", "openai").strip().lower()


async def generate_reply(system_prompt: str, messages: List[Dict[str, str]]) -> str:
    """Generate a counseling reply from the configured provider.

    Returns a non-empty string always: the provider's output, or ``FALLBACK_REPLY``
    if the provider is unset/unavailable or the call fails.
    """
    provider = _provider()
    try:
        if provider == "openai":
            return await _openai(system_prompt, messages) or FALLBACK_REPLY
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


async def _openai(system_prompt: str, messages: List[Dict[str, str]]) -> Optional[str]:
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        return None
    from openai import AsyncOpenAI  # lazy: absent SDK shouldn't break import

    client = AsyncOpenAI(api_key=key)
    model = os.environ.get("OPENAI_MODEL", "gpt-4o")
    convo = [{"role": "system", "content": system_prompt}, *_clean(messages)]
    resp = await client.chat.completions.create(
        model=model, max_tokens=MAX_REPLY_TOKENS, messages=convo
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
