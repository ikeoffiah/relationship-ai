MODEL_CONFIG = {
    'primary_counseling': {
        'model_id': 'claude-opus-4-6',
        'pinned_at': '2026-04-04',
        'fallback': 'claude-sonnet-4-6',
    },
    'fast_path': {'model_id': 'claude-haiku-4-5-20251001'},
    'safety_screening': {'model_id': 'claude-haiku-4-5-20251001'},
    # Post-session memory extraction: Haiku is cost-effective for structured extraction
    'memory_extraction': {
        'model_id': 'claude-haiku-4-5-20251001',
        'pinned_at': '2026-04-04',
    },
}
