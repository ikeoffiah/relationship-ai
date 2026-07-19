"""Unit tests for app/safety/layer4_behavioral.py."""

import pytest

from app.safety.layer4_behavioral import Layer4Result, screen_layer4


async def test_high_severity_event_requires_action():
    result = await screen_layer4("user-1", 0.95)

    assert isinstance(result, Layer4Result)
    assert result.score == 0.95
    assert result.action_required is True
    assert result.escalation_reason == "High severity safety event detected"


async def test_severity_exactly_at_threshold_requires_action():
    result = await screen_layer4("user-1", 0.8)

    assert result.action_required is True
    assert result.escalation_reason == "High severity safety event detected"


@pytest.mark.parametrize("severity", [0.0, 0.5, 0.79])
async def test_below_threshold_does_not_escalate(severity):
    result = await screen_layer4("user-1", severity)

    assert result.score == severity
    assert result.action_required is False
    assert result.escalation_reason == "No escalation needed"
