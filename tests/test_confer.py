"""CONFER gate: the bot-loop guard's one bounded exception."""

from clawcrew.agent import _confer_gate

ID_MAP = {"jerry": "U1", "kramer": "U2", "newman": "U3"}


def _bot_event(text, sender="U1", thread="123.45"):
    return {
        "bot_id": "B99",
        "user": sender,
        "text": text,
        "channel": "C1",
        "thread_ts": thread,
    }


def test_human_messages_always_pass():
    assert _confer_gate({"user": "UMATT", "text": "hi"}, ID_MAP, "kramer", {})


def test_bot_without_marker_blocked():
    assert not _confer_gate(_bot_event("hey kramer thoughts?"), ID_MAP, "kramer", {})


def test_confer_from_crew_bot_passes():
    assert _confer_gate(_bot_event("CONFER(2): why is the log empty?"), ID_MAP, "kramer", {})


def test_confer_zero_and_over_max_blocked():
    assert not _confer_gate(_bot_event("CONFER(0): done"), ID_MAP, "kramer", {})
    assert not _confer_gate(_bot_event("CONFER(4): loop?"), ID_MAP, "kramer", {})


def test_unknown_sender_blocked():
    assert not _confer_gate(_bot_event("CONFER(3): q", sender="U_EVIL"), ID_MAP, "kramer", {})


def test_own_message_blocked():
    assert not _confer_gate(_bot_event("CONFER(3): q", sender="U2"), ID_MAP, "kramer", {})


def test_rate_cap_three_per_thread_per_hour():
    log = {}
    ev = _bot_event("CONFER(3): q")
    assert _confer_gate(ev, ID_MAP, "kramer", log, now=1000.0)
    assert _confer_gate(ev, ID_MAP, "kramer", log, now=1010.0)
    assert _confer_gate(ev, ID_MAP, "kramer", log, now=1020.0)
    assert not _confer_gate(ev, ID_MAP, "kramer", log, now=1030.0)
    # window expires -> allowed again
    assert _confer_gate(ev, ID_MAP, "kramer", log, now=5000.0)
