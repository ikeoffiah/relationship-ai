"""Model selection per task path.

OpenAI is the default provider for every path — see ``llm_provider.py``
(counseling / tone coach) and ``extractor.py`` (memory extraction). The
Anthropic entries are consulted only when a path is explicitly switched to
Anthropic via ``LLM_PROVIDER=anthropic``.
"""

# Default (OpenAI) models per task path.
MODEL_CONFIG = {
    'primary_counseling': {'model_id': 'gpt-4o', 'fallback': 'gpt-4o-mini'},
    'fast_path': {'model_id': 'gpt-4o-mini'},
    'safety_screening': {'model_id': 'gpt-4o-mini'},
    # Post-session memory extraction: a mini model is cost-effective for
    # structured extraction.
    'memory_extraction': {'model_id': 'gpt-4o-mini'},
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
