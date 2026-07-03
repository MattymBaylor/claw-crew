from pathlib import Path

import pytest

from clawcrew.config import ConfigError, load_config


def test_placeholder_tokens_do_not_count_as_credentials(monkeypatch):
    crew = load_config()
    jerry = crew.agents[0]
    # Placeholder values (as shipped in .env.example) must read as missing.
    monkeypatch.setenv(jerry.bot_token_env, "xoxb-...")
    monkeypatch.setenv(jerry.app_token_env, "xapp-...")
    assert jerry.has_credentials is False
    # Real-looking values count.
    monkeypatch.setenv(jerry.bot_token_env, "xoxb-abc123")
    monkeypatch.setenv(jerry.app_token_env, "xapp-abc123")
    assert jerry.has_credentials is True


def test_default_roster_loads():
    crew = load_config()
    assert crew.name == "Open Claw"
    assert len(crew.agents) == 15
    assert "resources" in crew.required_channels
    assert "huddle" in crew.required_channels


def test_no_duplicates_in_default_roster():
    crew = load_config()
    assert crew.duplicates() == {}


def test_duplicate_detection(tmp_path: Path):
    roster = tmp_path / "roster.yaml"
    roster.write_text(
        """
crew:
  name: Test
agents:
  - { name: Jerry, handle: jerry, role: A }
  - { name: Jerry, handle: jerry2, role: B }
"""
    )
    crew = load_config(roster)
    dups = crew.duplicates()
    assert "name:jerry" in dups
    assert set(dups["name:jerry"]) == {"jerry", "jerry2"}


def test_missing_agents_raises(tmp_path: Path):
    roster = tmp_path / "roster.yaml"
    roster.write_text("crew:\n  name: Empty\n")
    with pytest.raises(ConfigError):
        load_config(roster)


def test_missing_required_field_raises(tmp_path: Path):
    roster = tmp_path / "roster.yaml"
    roster.write_text(
        "crew:\n  name: T\nagents:\n  - { name: NoHandle, role: X }\n"
    )
    with pytest.raises(ConfigError):
        load_config(roster)
