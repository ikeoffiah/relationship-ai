"""Model selection per task path.

OpenAI is the default provider for every path — see ``llm_provider.py``
(counseling / tone coach) and ``extractor.py`` (memory extraction). The
Anthropic entries are consulted only when a path is explicitly switched to
Anthropic via ``LLM_PROVIDER=anthropic``.
"""

# Default (OpenAI) models per task path.
#
# Latency is a product decision here, not just a cost one. Anything that runs
# while someone is mid-sentence — rephrasing a message to their partner,
# screening it before it sends, reading the mood of a thread — has to come back
# fast enough not to interrupt typing. Measured p50 on a representative rephrase
# prompt:
#
#     gpt-4.1-nano   0.86s   <- fast paths
#     gpt-4.1-mini   0.96s
#     gpt-5.4-mini   1.62s
#     gpt-4o-mini    2.05s   <- previous default
#
# (gpt-5-nano spent its whole token budget on reasoning and returned nothing;
# the gpt-5 reasoning family is the wrong tool for an inline assist.)
#
# The counseling reply deliberately stays on the stronger model: it is a
# considered response the user is waiting on, not an inline assist, and quality
# matters more than the second it costs.
MODEL_CONFIG = {
    'primary_counseling': {'model_id': 'gpt-4o', 'fallback': 'gpt-4.1-mini'},
    'fast_path': {'model_id': 'gpt-4.1-nano'},
    'safety_screening': {'model_id': 'gpt-4.1-nano'},
    # Post-session memory extraction: a nano model is plenty for structured
    # extraction and runs in the background.
    'memory_extraction': {'model_id': 'gpt-4.1-nano'},
}

# Opt-in Anthropic equivalents — used only when LLM_PROVIDER=anthropic.
ANTHROPIC_MODEL_CONFIG = {
    'primary_counseling': {
        'model_id': 'claude-opus-4-6',
        'pinned_at': '2026-04-04',
        'fallback': 'claude-sonnet-4-6',
    },
    'fast_path': {'model_id': 'claude-haiku-4-5-20251001'},
    'safety_screening': {'model_id': 'claude-haiku-4-5-20251001'},
    'memory_extraction': {
        'model_id': 'claude-haiku-4-5-20251001',
        'pinned_at': '2026-04-04',
    },
}
