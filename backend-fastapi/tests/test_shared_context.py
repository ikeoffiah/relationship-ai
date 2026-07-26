"""Tests for shared-context injection into the counseling prompt."""

from app.api.chat_router import _clean_list
from app.orchestration.graph import _shared_context_lines, build_system_prompt


# ── _clean_list (robust to JSONB-as-text + encrypted values) ─────────────

def test_clean_list_from_python_list():
    assert _clean_list(["chores", " in-laws ", ""]) == ["chores", "in-laws"]


def test_clean_list_from_jsonb_string():
    assert _clean_list('["money", "time apart"]') == ["money", "time apart"]


def test_clean_list_drops_encrypted_values():
    assert _clean_list(["ENC:abc123", "honesty"]) == ["honesty"]


def test_clean_list_handles_junk():
    assert _clean_list(None) == []
    assert _clean_list("not json") == []
    assert _clean_list("{}") == []  # dict, not a list


# ── _shared_context_lines (pure renderer) ────────────────────────────────

def test_shared_context_lines_goals_with_progress():
    lines = _shared_context_lines({
        "shared_goals": [
            {"title": "Save for a house", "category": "financial", "progress": "40%"},
            {"title": "Walk daily", "category": "health", "progress": ""},
        ],
    })
    assert any("Save for a house (40%)" in line for line in lines)
    assert any("Walk daily" in line for line in lines)


def test_shared_context_lines_conflicts_and_values():
    lines = _shared_context_lines({
        "recurring_conflicts": ["chores", "in-laws"],
        "agreed_values": ["honesty"],
    })
    joined = " ".join(lines)
    assert "chores" in joined and "in-laws" in joined
    assert "honesty" in joined


def test_shared_context_lines_empty():
    assert _shared_context_lines({}) == []
    assert _shared_context_lines({"shared_goals": [], "recurring_conflicts": []}) == []


def test_shared_context_lines_skips_goals_without_title():
    assert _shared_context_lines({"shared_goals": [{"category": "x"}]}) == []


# ── build_system_prompt integration ──────────────────────────────────────

def test_prompt_includes_shared_context_section():
    prompt = build_system_prompt(
        {}, {}, {}, [],
        shared_context={"shared_goals": [{"title": "Plan a trip", "progress": ""}]},
    )
    assert "Shared context for this couple" in prompt
    assert "Plan a trip" in prompt


def test_prompt_omits_section_when_no_shared_context():
    prompt = build_system_prompt({}, {}, {}, [], shared_context={})
    assert "Shared context for this couple" not in prompt


def test_prompt_still_builds_without_shared_context_arg():
    # Backward compatible: the new param is optional.
    prompt = build_system_prompt({}, {}, {}, [])
    assert prompt  # non-empty core identity
