from app.orchestration.model_config import MODEL_CONFIG
from app.orchestration.session_limiter import SessionFrequencyLimiter

def test_model_version_pinning():
    assert 'primary_counseling' in MODEL_CONFIG
    assert MODEL_CONFIG['primary_counseling']['model_id'] == 'claude-opus-4-6'
    assert MODEL_CONFIG['primary_counseling']['fallback'] == 'claude-sonnet-4-6'
    assert MODEL_CONFIG['fast_path']['model_id'] == 'claude-haiku-4-5-20251001'

def test_session_frequency_limiter():
    # Safe limits
    allow, show_prompt, msg = SessionFrequencyLimiter.check_limit(1, 4)
    assert allow is True
    assert show_prompt is False
    assert msg is None
    
    # Soft limit reached (daily)
    allow, show_prompt, msg = SessionFrequencyLimiter.check_limit(2, 4)
    assert allow is True
    assert show_prompt is True
    assert "multiple sessions today" in msg
    
    # Hard limit reached (daily)
    allow, show_prompt, msg = SessionFrequencyLimiter.check_limit(5, 6)
    assert allow is False
    assert show_prompt is False
    assert "Daily hard limit reached" in msg
    
    # Weekly threshold reached
    allow, show_prompt, msg = SessionFrequencyLimiter.check_limit(1, 7)
    assert allow is True
    assert show_prompt is True
    assert "highly active week" in msg
