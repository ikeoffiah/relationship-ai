"""Unit tests for app/memory/retriever.py (REL-89)."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.memory.retriever import (
    RECENCY_BOOST,
    RECENCY_WINDOW_DAYS,
    AccessPolicy,
    SessionMemoryRetriever,
    _apply_recency_boost,
)
from app.memory.vector_store import MemoryRecord


def record(memory_id, similarity, stored_at=None, metadata=None):
    if metadata is None:
        metadata = {} if stored_at is None else {"stored_at": stored_at}
    return MemoryRecord(memory_id=memory_id, metadata=metadata, similarity=similarity)


def iso_days_ago(days):
    return (datetime.now(tz=timezone.utc) - timedelta(days=days)).isoformat()


@pytest.fixture
def mock_store():
    """A VectorMemoryStore double whose .query is an AsyncMock."""
    store = MagicMock()
    store.query = AsyncMock(return_value=[])
    return store


@pytest.fixture
def retriever(mock_store):
    with patch("app.memory.retriever.VectorMemoryStore", return_value=mock_store):
        yield SessionMemoryRetriever(db_url="postgres://mock")


# ---------------------------------------------------------------------------
# _apply_recency_boost
# ---------------------------------------------------------------------------

def test_recent_memory_is_boosted():
    rec = record("m1", 0.50, stored_at=iso_days_ago(1))
    assert _apply_recency_boost(rec) == pytest.approx(0.50 * (1 + RECENCY_BOOST))


def test_memory_at_edge_of_window_is_boosted():
    rec = record("m1", 0.50, stored_at=iso_days_ago(RECENCY_WINDOW_DAYS - 1))
    assert _apply_recency_boost(rec) == pytest.approx(0.60)


def test_old_memory_is_not_boosted():
    rec = record("m1", 0.50, stored_at=iso_days_ago(RECENCY_WINDOW_DAYS + 10))
    assert _apply_recency_boost(rec) == 0.50


def test_naive_timestamp_is_treated_as_utc_and_boosted():
    naive = (datetime.now(tz=timezone.utc) - timedelta(days=2)).replace(tzinfo=None)
    rec = record("m1", 0.40, stored_at=naive.isoformat())
    assert _apply_recency_boost(rec) == pytest.approx(0.40 * (1 + RECENCY_BOOST))


def test_missing_stored_at_key_returns_raw_score():
    assert _apply_recency_boost(record("m1", 0.77, metadata={"other": 1})) == 0.77


def test_empty_metadata_returns_raw_score():
    assert _apply_recency_boost(record("m1", 0.77, metadata={})) == 0.77


def test_none_metadata_returns_raw_score():
    assert _apply_recency_boost(record("m1", 0.77, metadata=None)) == 0.77


def test_malformed_stored_at_returns_raw_score():
    assert _apply_recency_boost(record("m1", 0.66, stored_at="not-a-date")) == 0.66


def test_non_string_stored_at_returns_raw_score():
    assert _apply_recency_boost(record("m1", 0.66, metadata={"stored_at": 12345})) == 0.66


# ---------------------------------------------------------------------------
# retrieve_for_session
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_default_policy_queries_private_zone_only(retriever, mock_store):
    mock_store.query.return_value = [record("m1", 0.9)]

    results = await retriever.retrieve_for_session(
        user_id="u1", relationship_id="r1", opening_message="I feel overwhelmed"
    )

    assert mock_store.query.await_count == 1
    kwargs = mock_store.query.await_args.kwargs
    assert kwargs["zone"] == "private"
    assert kwargs["user_id"] == "u1"
    assert kwargs["query_text"] == "I feel overwhelmed"
    assert kwargs["top_k"] == 5
    assert [r.memory_id for r in results] == ["m1"]


@pytest.mark.asyncio
async def test_shared_consent_queries_both_zones(retriever, mock_store):
    mock_store.query.side_effect = [
        [record("priv-1", 0.9)],
        [record("shared-1", 0.8)],
    ]

    results = await retriever.retrieve_for_session(
        user_id="u1",
        relationship_id="r1",
        opening_message="hello",
        access_policy=AccessPolicy(can_read_private=True, can_read_shared_context=True),
    )

    zones = [c.kwargs["zone"] for c in mock_store.query.await_args_list]
    assert zones == ["private", "shared"]
    assert [r.memory_id for r in results] == ["priv-1", "shared-1"]


@pytest.mark.asyncio
async def test_private_disabled_skips_private_query(retriever, mock_store):
    mock_store.query.return_value = [record("shared-1", 0.8)]

    results = await retriever.retrieve_for_session(
        user_id="u1",
        relationship_id="r1",
        opening_message="hello",
        access_policy=AccessPolicy(can_read_private=False, can_read_shared_context=True),
    )

    assert mock_store.query.await_count == 1
    assert mock_store.query.await_args.kwargs["zone"] == "shared"
    assert [r.memory_id for r in results] == ["shared-1"]


@pytest.mark.asyncio
async def test_policy_denying_everything_makes_no_queries(retriever, mock_store):
    results = await retriever.retrieve_for_session(
        user_id="u1",
        relationship_id="r1",
        opening_message="hello",
        access_policy=AccessPolicy(can_read_private=False, can_read_shared_context=False),
    )

    assert results == []
    mock_store.query.assert_not_awaited()


@pytest.mark.asyncio
async def test_custom_top_k_values_are_forwarded(retriever, mock_store):
    await retriever.retrieve_for_session(
        user_id="u1",
        relationship_id="r1",
        opening_message="hello",
        access_policy=AccessPolicy(can_read_shared_context=True),
        top_k_private=9,
        top_k_shared=2,
    )

    calls = mock_store.query.await_args_list
    assert calls[0].kwargs["top_k"] == 9
    assert calls[1].kwargs["top_k"] == 2


@pytest.mark.asyncio
async def test_duplicate_memory_id_across_zones_is_deduped(retriever, mock_store):
    mock_store.query.side_effect = [
        [record("dup", 0.9), record("priv-only", 0.5)],
        [record("dup", 0.4), record("shared-only", 0.3)],
    ]

    results = await retriever.retrieve_for_session(
        user_id="u1",
        relationship_id="r1",
        opening_message="hello",
        access_policy=AccessPolicy(can_read_shared_context=True),
    )

    ids = [r.memory_id for r in results]
    assert ids.count("dup") == 1
    assert set(ids) == {"dup", "priv-only", "shared-only"}
    # The private-zone copy (0.9) is the one that survived, not the shared 0.4.
    assert next(r for r in results if r.memory_id == "dup").similarity == 0.9


@pytest.mark.asyncio
async def test_duplicates_within_one_zone_are_deduped(retriever, mock_store):
    mock_store.query.return_value = [record("m1", 0.9), record("m1", 0.7)]

    results = await retriever.retrieve_for_session(
        user_id="u1", relationship_id="r1", opening_message="hello"
    )

    assert [r.memory_id for r in results] == ["m1"]


@pytest.mark.asyncio
async def test_results_sorted_by_adjusted_score_descending(retriever, mock_store):
    # "old-high" has the better raw score, but "new-mid" gets the recency boost
    # (0.80 * 1.2 = 0.96) which pushes it above 0.90.
    mock_store.query.return_value = [
        record("old-high", 0.90, stored_at=iso_days_ago(200)),
        record("new-mid", 0.80, stored_at=iso_days_ago(2)),
        record("old-low", 0.10, stored_at=iso_days_ago(300)),
    ]

    results = await retriever.retrieve_for_session(
        user_id="u1", relationship_id="r1", opening_message="hello"
    )

    assert [r.memory_id for r in results] == ["new-mid", "old-high", "old-low"]


@pytest.mark.asyncio
async def test_empty_store_returns_empty_list(retriever, mock_store):
    mock_store.query.return_value = []

    results = await retriever.retrieve_for_session(
        user_id="u1", relationship_id="r1", opening_message="hello"
    )

    assert results == []


def test_retriever_constructs_vector_store_with_db_url(mock_store):
    with patch(
        "app.memory.retriever.VectorMemoryStore", return_value=mock_store
    ) as mock_cls:
        SessionMemoryRetriever(db_url="postgres://example")

    mock_cls.assert_called_once_with(db_url="postgres://example")


def test_default_access_policy_is_private_only():
    policy = AccessPolicy()
    assert policy.can_read_private is True
    assert policy.can_read_shared_context is False
