"""Unit tests for app/memory/trigger_builder.py (REL-89)."""

import pytest

from app.memory.trigger_builder import (
    INVENTORY_MAX_SIZE,
    TriggerInventoryBuilder,
    _is_distress_marker,
    _is_exit_signal,
)


@pytest.fixture
def builder():
    """Fresh builder with its own isolated store (never the module-level one)."""
    return TriggerInventoryBuilder(store={})


def user(content):
    return {"role": "user", "content": content}


def assistant(content):
    return {"role": "assistant", "content": content}


# ---------------------------------------------------------------------------
# _is_distress_marker
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "text",
    [
        "This is hard to say, but I've been unhappy.",
        "I don't want to talk about this",
        "I don't know how to talk about this right now",
        "I don't know where to start",
        "It's painful every time it comes up",
        "This is difficult for me",
        "I feel overwhelmed by all of it",
        "I feel scared",
        "I can't do this anymore",
        "I can't talk about this",
        "please don't push me on it",
        "Please don't ask me that",
    ],
)
def test_distress_markers_are_detected(text):
    assert _is_distress_marker(text) is True


@pytest.mark.parametrize(
    "text",
    [
        "We had a good weekend together.",
        "I want to talk about this openly",
        "I feel happy about how things went",
        "",
    ],
)
def test_non_distress_text_is_not_detected(text):
    assert _is_distress_marker(text) is False


def test_distress_marker_detection_is_case_insensitive():
    assert _is_distress_marker("THIS IS HARD TO SAY") is True


# ---------------------------------------------------------------------------
# _is_exit_signal
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "text",
    ["ok", "Fine", "whatever", "I'm done", "stop", "never mind", "nevermind",
     "forget it", "goodbye", "bye"],
)
def test_exit_signals_are_detected(text):
    assert _is_exit_signal(text) is True


def test_exit_signal_strips_trailing_punctuation_and_whitespace():
    assert _is_exit_signal("  Fine!!  ") is True
    assert _is_exit_signal("bye.") is True


@pytest.mark.parametrize(
    "text",
    ["ok but I want to keep going", "that's fine with me", "I am not done", ""],
)
def test_non_exit_text_is_not_detected(text):
    assert _is_exit_signal(text) is False


# ---------------------------------------------------------------------------
# update_triggers
# ---------------------------------------------------------------------------

def test_assistant_messages_are_ignored(builder):
    messages = [
        assistant("This is hard to say, I know."),
        assistant("ok"),
    ]
    inventory = builder.update_triggers(messages, "u1", "sess-1")

    assert inventory == []


def test_neutral_conversation_produces_no_triggers(builder):
    messages = [
        user("We went hiking on Saturday."),
        assistant("That sounds nice."),
        user("It was a good day and we talked a lot."),
    ]
    assert builder.update_triggers(messages, "u1", "sess-1") == []


def test_distress_marker_produces_severity_two_trigger(builder):
    messages = [
        user("This is hard to say but I've felt distant."),
        assistant("Take your time."),
        user("We had dinner after that."),
        user("And then we watched a movie."),
    ]
    inventory = builder.update_triggers(messages, "u1", "sess-1")

    assert len(inventory) == 1
    trigger = inventory[0]
    assert trigger.tone == "distress_marker"
    assert trigger.severity == 2
    assert trigger.confidence == 0.75
    assert trigger.session_id == "sess-1"
    assert trigger.topic == "This is hard to say but I've felt distant."


def test_distress_marker_topic_is_truncated_to_100_chars(builder):
    long_tail = "x" * 200
    messages = [
        user(f"This is hard to say {long_tail}"),
        user("filler one"),
        user("filler two"),
    ]
    inventory = builder.update_triggers(messages, "u1", "sess-1")

    assert len(inventory[0].topic) == 100


def test_exit_signal_near_end_takes_topic_from_previous_user_message(builder):
    messages = [
        user("Things have been busy at work."),
        assistant("Tell me more."),
        user("My mother keeps calling about the wedding."),
        assistant("How does that land for you?"),
        user("fine"),
    ]
    inventory = builder.update_triggers(messages, "u1", "sess-2")

    assert len(inventory) == 1
    trigger = inventory[0]
    assert trigger.tone == "withdrawal"
    assert trigger.severity == 3
    assert trigger.confidence == 0.7
    assert trigger.session_id == "sess-2"
    assert trigger.topic == "My mother keeps calling about the wedding."


def test_exit_signal_early_in_session_is_ignored(builder):
    messages = [
        user("ok"),
        user("Then we talked about the budget."),
        user("It went reasonably well."),
        user("And we agreed on a plan."),
    ]
    assert builder.update_triggers(messages, "u1", "sess-2") == []


def test_exit_signal_as_first_message_falls_back_to_its_own_content(builder):
    inventory = builder.update_triggers([user("stop")], "u1", "sess-3")

    assert len(inventory) == 1
    assert inventory[0].topic == "stop"
    assert inventory[0].tone == "withdrawal"


def test_distress_marker_wins_over_exit_signal_on_same_message(builder):
    # "i can't do this" is both a distress marker and the final user message.
    inventory = builder.update_triggers(
        [user("I said we'd talk"), user("i can't do this")], "u1", "sess-4"
    )

    tones = [t.tone for t in inventory]
    assert "distress_marker" in tones
    assert "withdrawal" not in tones


def test_multiple_triggers_accumulate_across_calls(builder):
    builder.update_triggers(
        [user("This is hard to say."), user("a"), user("b")], "u1", "sess-1"
    )
    inventory = builder.update_triggers(
        [user("I feel anxious about it."), user("a"), user("b")], "u1", "sess-2"
    )

    assert len(inventory) == 2
    assert [t.session_id for t in inventory] == ["sess-1", "sess-2"]


def test_inventory_is_capped_and_evicts_oldest_first(builder):
    total = INVENTORY_MAX_SIZE + 5
    for i in range(total):
        builder.update_triggers(
            [user("This is hard to say."), user("a"), user("b")], "u1", f"sess-{i}"
        )

    inventory = builder.get_triggers("u1")
    assert len(inventory) == INVENTORY_MAX_SIZE
    # Oldest (sess-0 .. sess-4) evicted; the newest survive in order.
    assert [t.session_id for t in inventory] == [
        f"sess-{i}" for i in range(total - INVENTORY_MAX_SIZE, total)
    ]


def test_triggers_are_scoped_per_user(builder):
    messages = [user("This is hard to say."), user("a"), user("b")]
    builder.update_triggers(messages, "user-a", "s1")

    assert len(builder.get_triggers("user-a")) == 1
    assert builder.get_triggers("user-b") == []


# ---------------------------------------------------------------------------
# get_triggers / clear_user_data
# ---------------------------------------------------------------------------

def test_get_triggers_for_unknown_user_is_empty(builder):
    assert builder.get_triggers("nobody") == []


def test_clear_user_data_removes_only_that_user(builder):
    messages = [user("This is hard to say."), user("a"), user("b")]
    builder.update_triggers(messages, "user-a", "s1")
    builder.update_triggers(messages, "user-b", "s1")

    builder.clear_user_data("user-a")

    assert builder.get_triggers("user-a") == []
    assert len(builder.get_triggers("user-b")) == 1


def test_clear_user_data_is_idempotent(builder):
    builder.clear_user_data("never-existed")
    assert builder.get_triggers("never-existed") == []


def test_builder_uses_the_injected_store():
    store: dict = {}
    injected = TriggerInventoryBuilder(store=store)
    injected.update_triggers(
        [user("This is hard to say."), user("a"), user("b")], "u1", "s1"
    )

    assert list(store.keys()) == ["u1"]
    assert store["u1"][0].tone == "distress_marker"
