"""Unit tests for app/memory/conflict_tracker.py (REL-89)."""

from dataclasses import dataclass

import pytest

from app.memory.conflict_tracker import (
    RECURRING_THRESHOLD,
    SIMILARITY_THRESHOLD,
    ConflictPattern,
    ConflictPatternTracker,
    _token_overlap_similarity,
)


@dataclass
class FakeMemory:
    """Stand-in for MemoryCandidate (only .content/.memory_type are read)."""

    content: str
    memory_type: str


@pytest.fixture
def tracker():
    """Fresh tracker with its own isolated store (never the module-level one)."""
    return ConflictPatternTracker(store={})


# ---------------------------------------------------------------------------
# _token_overlap_similarity
# ---------------------------------------------------------------------------

def test_similarity_identical_labels_is_one():
    assert _token_overlap_similarity("money and chores", "money and chores") == 1.0


def test_similarity_is_case_insensitive():
    assert _token_overlap_similarity("Money And Chores", "money and chores") == 1.0


def test_similarity_disjoint_labels_is_zero():
    assert _token_overlap_similarity("money stress", "vacation planning") == 0.0


def test_similarity_partial_overlap_is_jaccard():
    # tokens: {a, b, c} vs {b, c, d} -> intersection 2, union 4
    assert _token_overlap_similarity("a b c", "b c d") == 0.5


def test_similarity_empty_label_is_zero():
    assert _token_overlap_similarity("", "money stress") == 0.0
    assert _token_overlap_similarity("money stress", "") == 0.0
    assert _token_overlap_similarity("", "") == 0.0


# ---------------------------------------------------------------------------
# update_conflict_history
# ---------------------------------------------------------------------------

def test_non_conflict_memories_are_ignored(tracker):
    memories = [
        FakeMemory("user prefers direct feedback", "communication_style"),
        FakeMemory("user needs more alone time", "stated_need"),
    ]
    patterns = tracker.update_conflict_history("s1", "u1", memories)

    assert patterns == []
    assert tracker.get_patterns("u1") == []


def test_empty_memory_list_returns_existing_patterns(tracker):
    tracker.update_conflict_history("s1", "u1", [FakeMemory("money stress", "conflict_pattern")])
    patterns = tracker.update_conflict_history("s2", "u1", [])

    assert len(patterns) == 1
    assert patterns[0].occurrence_count == 1
    assert patterns[0].last_seen_session == "s1"


def test_new_pattern_is_created_with_provenance(tracker):
    patterns = tracker.update_conflict_history(
        "session-1", "u1", [FakeMemory("arguments about money", "conflict_pattern")]
    )

    assert len(patterns) == 1
    pattern = patterns[0]
    assert pattern.label == "arguments about money"
    assert pattern.user_id == "u1"
    assert pattern.occurrence_count == 1
    assert pattern.first_seen_session == "session-1"
    assert pattern.last_seen_session == "session-1"
    assert pattern.evidence_sessions == ["session-1"]
    assert pattern.is_recurring is False
    assert pattern.pattern_id  # a uuid was assigned


def test_dissimilar_label_creates_a_second_pattern(tracker):
    tracker.update_conflict_history(
        "s1", "u1", [FakeMemory("arguments about money", "conflict_pattern")]
    )
    patterns = tracker.update_conflict_history(
        "s2", "u1", [FakeMemory("tension over in-law visits", "conflict_pattern")]
    )

    assert len(patterns) == 2
    assert {p.label for p in patterns} == {
        "arguments about money",
        "tension over in-law visits",
    }
    assert all(p.occurrence_count == 1 for p in patterns)


def test_similar_label_increments_existing_pattern(tracker):
    tracker.update_conflict_history(
        "s1", "u1", [FakeMemory("arguments about money", "conflict_pattern")]
    )
    # Identical label -> similarity 1.0 >= SIMILARITY_THRESHOLD
    patterns = tracker.update_conflict_history(
        "s2", "u1", [FakeMemory("arguments about money", "conflict_pattern")]
    )

    assert len(patterns) == 1
    assert patterns[0].occurrence_count == 2
    assert patterns[0].first_seen_session == "s1"
    assert patterns[0].last_seen_session == "s2"
    assert patterns[0].evidence_sessions == ["s1", "s2"]
    assert patterns[0].is_recurring is False


def test_similarity_just_below_threshold_does_not_match(tracker):
    # {a,b,c,d} vs {a,b,c,e} -> 3/5 = 0.6 < 0.85
    tracker.update_conflict_history("s1", "u1", [FakeMemory("a b c d", "conflict_pattern")])
    patterns = tracker.update_conflict_history(
        "s2", "u1", [FakeMemory("a b c e", "conflict_pattern")]
    )

    assert _token_overlap_similarity("a b c d", "a b c e") < SIMILARITY_THRESHOLD
    assert len(patterns) == 2


def test_becomes_recurring_at_threshold(tracker):
    memory = FakeMemory("we fight about chores", "conflict_pattern")
    for i in range(RECURRING_THRESHOLD - 1):
        patterns = tracker.update_conflict_history(f"s{i}", "u1", [memory])
        assert patterns[0].is_recurring is False

    patterns = tracker.update_conflict_history("s-final", "u1", [memory])

    assert patterns[0].occurrence_count == RECURRING_THRESHOLD
    assert patterns[0].is_recurring is True


def test_repeat_session_id_is_not_duplicated_in_evidence(tracker):
    memory = FakeMemory("we fight about chores", "conflict_pattern")
    tracker.update_conflict_history("same-session", "u1", [memory])
    patterns = tracker.update_conflict_history("same-session", "u1", [memory])

    assert patterns[0].occurrence_count == 2
    assert patterns[0].evidence_sessions == ["same-session"]


def test_two_conflict_memories_in_one_call(tracker):
    patterns = tracker.update_conflict_history(
        "s1",
        "u1",
        [
            FakeMemory("money disagreements", "conflict_pattern"),
            FakeMemory("money disagreements", "conflict_pattern"),
            FakeMemory("household chores split", "conflict_pattern"),
        ],
    )

    assert len(patterns) == 2
    by_label = {p.label: p for p in patterns}
    assert by_label["money disagreements"].occurrence_count == 2
    assert by_label["household chores split"].occurrence_count == 1


def test_patterns_are_scoped_per_user(tracker):
    memory = FakeMemory("money disagreements", "conflict_pattern")
    tracker.update_conflict_history("s1", "user-a", [memory])
    tracker.update_conflict_history("s1", "user-b", [memory])
    tracker.update_conflict_history("s2", "user-b", [memory])

    assert tracker.get_patterns("user-a")[0].occurrence_count == 1
    assert tracker.get_patterns("user-b")[0].occurrence_count == 2


# ---------------------------------------------------------------------------
# get_patterns / clear_user_data
# ---------------------------------------------------------------------------

def test_get_patterns_for_unknown_user_is_empty(tracker):
    assert tracker.get_patterns("nobody") == []


def test_clear_user_data_removes_only_that_user(tracker):
    memory = FakeMemory("money disagreements", "conflict_pattern")
    tracker.update_conflict_history("s1", "user-a", [memory])
    tracker.update_conflict_history("s1", "user-b", [memory])

    tracker.clear_user_data("user-a")

    assert tracker.get_patterns("user-a") == []
    assert len(tracker.get_patterns("user-b")) == 1


def test_clear_user_data_is_idempotent(tracker):
    tracker.clear_user_data("never-existed")
    assert tracker.get_patterns("never-existed") == []


def test_tracker_uses_the_injected_store(tracker):
    store: dict = {}
    injected = ConflictPatternTracker(store=store)
    injected.update_conflict_history(
        "s1", "u1", [FakeMemory("money disagreements", "conflict_pattern")]
    )

    assert list(store.keys()) == ["u1"]
    assert isinstance(store["u1"][0], ConflictPattern)
