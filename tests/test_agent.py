"""Tests for the pure event-keying helpers in agent.py.

These cover the write key vs. the (thread-inheriting) read key list without
needing Slack or Anthropic — those are imported lazily inside build()/start().
"""

from clawcrew.agent import _conversation_key, _history_keys, _strip_mentions


def test_conversation_key_channel():
    assert _conversation_key({"channel": "C1"}) == "C1"


def test_conversation_key_thread_is_scoped():
    assert _conversation_key({"channel": "C1", "thread_ts": "111.22"}) == "C1:111.22"


def test_history_keys_channel_only():
    assert _history_keys({"channel": "C1"}) == ["C1"]


def test_history_keys_thread_inherits_parent_channel():
    # Parent channel first (inherited base), then the thread's own scope.
    assert _history_keys({"channel": "C1", "thread_ts": "111.22"}) == ["C1", "C1:111.22"]


def test_write_key_is_last_read_key_in_thread():
    event = {"channel": "C1", "thread_ts": "111.22"}
    assert _conversation_key(event) == _history_keys(event)[-1]


def test_strip_mentions():
    assert _strip_mentions("<@U123> hello there") == "hello there"
    assert _strip_mentions("no mentions") == "no mentions"
