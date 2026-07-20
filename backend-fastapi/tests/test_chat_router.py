"""Unit tests for app/api/chat_router.py (counseling SSE stream)."""

import json

import pytest
from fastapi.testclient import TestClient

from app.api import chat_router as chat
from app.main import app
from tests.conftest import auth_headers

client = TestClient(app)

SESSION = "session-1"
USER = "user-a"
HEADERS = auth_headers(USER)
URL = f"/api/v1/sessions/{SESSION}/messages"


def parse_sse(body: str) -> list[dict]:
    """Decode an SSE body the way the Flutter client does."""
    events = []
    for line in body.split("\n"):
        if not line.startswith("data: "):
            continue
        payload = line[6:].strip()
        if payload:
            events.append(json.loads(payload))
    return events


def post(content="I feel unheard lately.", headers=HEADERS):
    return client.post(URL, json={"content": content}, headers=headers)


# ---------------------------------------------------------------------------
# transport
# ---------------------------------------------------------------------------

def test_response_is_an_event_stream():
    res = post()
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("text/event-stream")
    # Proxy buffering would defeat streaming entirely.
    assert res.headers["x-accel-buffering"] == "no"
    assert res.headers["cache-control"] == "no-cache"


def test_requires_authentication():
    res = client.post(URL, json={"content": "hello"})
    assert res.status_code == 401


def test_rejects_missing_content():
    res = client.post(URL, json={}, headers=HEADERS)
    assert res.status_code == 422


# ---------------------------------------------------------------------------
# event contract
# ---------------------------------------------------------------------------

def test_every_frame_is_single_line_json():
    """The client splits the byte stream on newlines, so a multi-line payload
    would be silently dropped."""
    events = parse_sse(post().text)
    assert events
    for line in post().text.split("\n"):
        if line.startswith("data: "):
            json.loads(line[6:].strip())  # raises if a payload spans lines


def test_stream_ends_with_done():
    events = parse_sse(post().text)
    assert events[-1] == {"type": "done"}


def test_emits_only_event_types_the_client_understands():
    known = {
        "token",
        "strategy_change",
        "safety_triggered",
        "reframe_available",
        "turn_held",
        "de_escalation_triggered",
        "done",
    }
    for event in parse_sse(post().text):
        assert event["type"] in known


def test_tokens_reassemble_into_the_model_output():
    events = parse_sse(post().text)
    tokens = [e["content"] for e in events if e["type"] == "token"]
    assert tokens, "expected the reply to be streamed as token frames"
    reassembled = "".join(tokens)
    assert reassembled.strip()
    # node_9 appends a pacing marker, so its presence proves the stream
    # carries the fully-formatted output rather than a raw LLM string.
    assert "[Pacing: Relaxed]" in reassembled


def test_token_frames_are_chunked():
    events = parse_sse(post().text)
    tokens = [e["content"] for e in events if e["type"] == "token"]
    assert all(len(t) <= chat.TOKEN_CHUNK_SIZE for t in tokens)


def test_strategy_change_is_emitted_with_a_strategy():
    events = parse_sse(post().text)
    strategies = [e for e in events if e["type"] == "strategy_change"]
    assert strategies
    assert all(s["strategy"] for s in strategies)


# ---------------------------------------------------------------------------
# safety
# ---------------------------------------------------------------------------

def test_safety_event_emitted_for_crisis_message():
    events = parse_sse(post(content="I want to kill myself").text)
    safety = [e for e in events if e["type"] == "safety_triggered"]
    assert safety, "a crisis disclosure must raise a safety event"
    assert safety[0]["level"] in ("elevated", "critical")
    assert isinstance(safety[0]["resources"], list)
    # Still terminates cleanly so the client is not left hanging.
    assert events[-1] == {"type": "done"}


def test_safety_event_emitted_at_most_once():
    events = parse_sse(post(content="I want to kill myself").text)
    assert len([e for e in events if e["type"] == "safety_triggered"]) <= 1


def test_benign_message_raises_no_safety_event():
    events = parse_sse(post(content="We had a nice weekend together.").text)
    assert not [e for e in events if e["type"] == "safety_triggered"]


# ---------------------------------------------------------------------------
# crisis resources
# ---------------------------------------------------------------------------

def test_resources_empty_when_unconfigured(monkeypatch):
    monkeypatch.delenv("CRISIS_RESOURCES", raising=False)
    assert chat.crisis_resources() == []


def test_resources_read_from_configuration(monkeypatch):
    configured = [{"name": "Example Line", "phone": "000", "url": "https://example.org"}]
    monkeypatch.setenv("CRISIS_RESOURCES", json.dumps(configured))
    assert chat.crisis_resources() == configured


@pytest.mark.parametrize("bad", ["not json", '{"not": "a list"}', ""])
def test_malformed_resource_config_degrades_to_empty(monkeypatch, bad):
    """A bad config must not surface garbage to someone in crisis, nor 500."""
    monkeypatch.setenv("CRISIS_RESOURCES", bad)
    assert chat.crisis_resources() == []


# ---------------------------------------------------------------------------
# failure handling
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_done_is_emitted_even_if_the_graph_fails(monkeypatch):
    """The client waits for `done`; a mid-stream failure must not hang it."""

    class Boom:
        def astream(self, *a, **k):
            raise RuntimeError("orchestration exploded")

    monkeypatch.setattr(chat, "build_counseling_graph", lambda: Boom())

    frames = []
    with pytest.raises(RuntimeError):
        async for frame in chat.stream_counseling_turn(SESSION, USER, "hi"):
            frames.append(frame)

    assert frames, "the finally block must still emit a terminating frame"
    assert json.loads(frames[-1][6:].strip()) == {"type": "done"}
