"""Tests for the pure Slack app manifest builders (no network)."""

from __future__ import annotations

from clawcrew.config import load_config
from clawcrew.manifest import (
    BOT_EVENTS,
    BOT_SCOPES,
    build_manifest,
    manifests_for_crew,
)


def _first_agent(crew):
    # Roster-agnostic: exercise the builders against whoever is first in the
    # roster so swapping the crew never breaks these tests.
    return crew.agents[0]


def test_build_manifest_names_and_bot_user():
    crew = load_config()
    agent = _first_agent(crew)
    m = build_manifest(agent, crew)

    assert m["display_information"]["name"] == agent.name
    bot_user = m["features"]["bot_user"]
    assert bot_user["display_name"] == agent.handle
    assert bot_user["always_online"] is True


def test_build_manifest_scopes_match_readme():
    crew = load_config()
    m = build_manifest(_first_agent(crew), crew)
    expected = [
        "app_mentions:read",
        "channels:read",
        "channels:join",
        "chat:write",
        "im:history",
        "im:read",
        "im:write",
        "users:read",
    ]
    assert m["oauth_config"]["scopes"]["bot"] == expected
    assert list(BOT_SCOPES) == expected


def test_build_manifest_events_and_socket_settings():
    crew = load_config()
    m = build_manifest(_first_agent(crew), crew)
    settings = m["settings"]

    assert m["settings"]["event_subscriptions"]["bot_events"] == ["app_mention", "message.im"]
    assert list(BOT_EVENTS) == ["app_mention", "message.im"]
    assert settings["socket_mode_enabled"] is True
    assert settings["interactivity"]["is_enabled"] is False


def test_manifests_for_crew_one_entry_per_agent():
    crew = load_config()
    manifests = manifests_for_crew(crew)

    assert len(manifests) == len(crew.agents)
    assert set(manifests) == {a.handle for a in crew.agents}
    for agent in crew.agents:
        assert manifests[agent.handle]["display_information"]["name"] == agent.name
