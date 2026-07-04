"""Mention safety net: bare IDs and @handles become real pinging mentions."""

from clawcrew.agent import _linkify_mentions

ID_MAP = {"jerry": "U0BF6GJN3FW", "kramer": "U0ANA5QN4CF", "newman": "U0BF50FAZQ9"}


def test_bare_id_gets_brackets():
    assert _linkify_mentions("@U0BF50FAZQ9 CONFER(3): q", ID_MAP) == "<@U0BF50FAZQ9> CONFER(3): q"


def test_already_bracketed_untouched():
    assert _linkify_mentions("<@U0BF50FAZQ9> hi", ID_MAP) == "<@U0BF50FAZQ9> hi"


def test_plain_handle_becomes_mention():
    assert _linkify_mentions("ask @kramer about n8n", ID_MAP) == "ask <@U0ANA5QN4CF> about n8n"


def test_unknown_handle_untouched():
    assert _linkify_mentions("email @matt today", ID_MAP) == "email @matt today"


def test_case_insensitive_handles():
    assert _linkify_mentions("@Kramer giddy up", ID_MAP) == "<@U0ANA5QN4CF> giddy up"
