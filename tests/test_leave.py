"""Tests for leave_channel using a faked slack_sdk (no network).

Pins the fix for the rate-limit bug: the channel is resolved with ONE listing
call total (not one per agent), not_in_channel is skipped quietly, and any
other Slack error surfaces instead of being swallowed.
"""

from __future__ import annotations

import sys
import types

import pytest

from clawcrew import provision
from clawcrew.config import load_config


class FakeSlackApiError(Exception):
    def __init__(self, error: str):
        self.response = {"error": error}
        super().__init__(error)


class FakeState:
    def __init__(self):
        self.list_calls = 0
        self.leave_calls: list[str] = []
        self.leave_errors: dict[str, str] = {}  # token -> slack error string


def _install_fake_slack(monkeypatch, state: FakeState):
    class FakeWebClient:
        def __init__(self, token=None):
            self.token = token
            self.retry_handlers = []

        def conversations_list(self, **kwargs):
            state.list_calls += 1
            return {
                "channels": [
                    {"id": "C1", "name": "general", "is_member": True},
                    {"id": "C9", "name": "matts-office", "is_member": True},
                ],
                "response_metadata": {},
            }

        def conversations_leave(self, channel):
            err = state.leave_errors.get(self.token)
            if err:
                raise FakeSlackApiError(err)
            state.leave_calls.append(self.token)
            return {"ok": True}

    sdk = types.ModuleType("slack_sdk")
    sdk.WebClient = FakeWebClient
    errors = types.ModuleType("slack_sdk.errors")
    errors.SlackApiError = FakeSlackApiError
    retry = types.ModuleType("slack_sdk.http_retry")
    handlers = types.ModuleType("slack_sdk.http_retry.builtin_handlers")
    handlers.RateLimitErrorRetryHandler = lambda max_retry_count=3: object()

    for name, mod in {
        "slack_sdk": sdk,
        "slack_sdk.errors": errors,
        "slack_sdk.http_retry": retry,
        "slack_sdk.http_retry.builtin_handlers": handlers,
    }.items():
        monkeypatch.setitem(sys.modules, name, mod)


def _credential_all(monkeypatch, crew):
    for agent in crew.agents:
        monkeypatch.setenv(agent.bot_token_env, f"xoxb-{agent.handle}")
        monkeypatch.setenv(agent.app_token_env, f"xapp-{agent.handle}")


def test_leave_resolves_channel_once_and_leaves_per_agent(monkeypatch):
    state = FakeState()
    _install_fake_slack(monkeypatch, state)
    crew = load_config()
    _credential_all(monkeypatch, crew)

    left = provision.leave_channel(crew, "#Matts-Office")

    assert len(left) == len(crew.agents)
    # The whole point of the fix: one listing call total, not one per agent.
    assert state.list_calls == 1
    assert len(state.leave_calls) == len(crew.agents)


def test_leave_dry_run_makes_no_leave_calls(monkeypatch):
    state = FakeState()
    _install_fake_slack(monkeypatch, state)
    crew = load_config()
    _credential_all(monkeypatch, crew)

    left = provision.leave_channel(crew, "matts-office", dry_run=True)

    assert len(left) == len(crew.agents)
    assert state.leave_calls == []


def test_leave_skips_not_in_channel_but_raises_other_errors(monkeypatch):
    state = FakeState()
    _install_fake_slack(monkeypatch, state)
    crew = load_config()
    _credential_all(monkeypatch, crew)

    absent = f"xoxb-{crew.agents[0].handle}"
    state.leave_errors[absent] = "not_in_channel"
    left = provision.leave_channel(crew, "matts-office")
    assert crew.agents[0].handle not in left
    assert len(left) == len(crew.agents) - 1

    # Rate limits and other errors must surface, not be swallowed.
    state.leave_errors[f"xoxb-{crew.agents[1].handle}"] = "ratelimited"
    with pytest.raises(FakeSlackApiError):
        provision.leave_channel(crew, "matts-office")


def test_leave_unknown_channel_returns_empty(monkeypatch):
    state = FakeState()
    _install_fake_slack(monkeypatch, state)
    crew = load_config()
    _credential_all(monkeypatch, crew)

    assert provision.leave_channel(crew, "no-such-room") == []
    assert state.leave_calls == []
