"""Tests for the pure parts of slack_admin (no network)."""

from __future__ import annotations

import json

from clawcrew import slack_admin
from clawcrew.config import load_config


def test_select_agents_skips_ledger_and_skip_list():
    crew = load_config()
    ledger = {"jerry": {"app_id": "A1", "name": "Jerry"}}
    selected = slack_admin.select_agents(crew, ledger, skip=["kramer"])
    handles = {a.handle for a in selected}
    assert "jerry" not in handles  # already in ledger
    assert "kramer" not in handles  # explicitly skipped
    assert "elaine" in handles
    assert len(selected) == len(crew.agents) - 2


def test_select_agents_only():
    crew = load_config()
    selected = slack_admin.select_agents(crew, {}, only=["@george", "newman"])
    assert {a.handle for a in selected} == {"george", "newman"}


def test_ledger_round_trip(tmp_path):
    path = tmp_path / "slack-apps.json"
    assert slack_admin.load_ledger(path) == {}
    data = {"jerry": {"app_id": "A0BEWGPCZH9", "name": "Jerry"}}
    slack_admin.save_ledger(data, path)
    assert slack_admin.load_ledger(path) == data


def test_bootstrap_dry_run_needs_no_token(tmp_path):
    crew = load_config()
    ledger = tmp_path / "slack-apps.json"
    results = slack_admin.bootstrap(crew, None, dry_run=True, ledger_path=ledger)
    assert len(results) == len(crew.agents)
    assert all(r.skipped_reason == "dry-run" for r in results)
    assert not ledger.exists()  # dry run writes nothing


def test_bootstrap_records_created_apps(tmp_path, monkeypatch):
    crew = load_config()
    ledger = tmp_path / "slack-apps.json"

    calls = {"n": 0}

    def fake_post(method, token, params):
        calls["n"] += 1
        assert method == "apps.manifest.create"
        assert token == "xoxe.xoxp-test"
        json.loads(params["manifest"])  # must be valid JSON
        return {"ok": True, "app_id": f"A{calls['n']:03d}"}

    monkeypatch.setattr(slack_admin, "_post", fake_post)
    results = slack_admin.bootstrap(
        crew, "xoxe.xoxp-test", only=["jerry", "kramer"], ledger_path=ledger
    )
    assert [r.app_id for r in results] == ["A001", "A002"]
    assert all(r.created for r in results)
    # Ledger persisted so a re-run skips them.
    saved = slack_admin.load_ledger(ledger)
    assert set(saved) == {"jerry", "kramer"}
    rerun = slack_admin.bootstrap(crew, "xoxe.xoxp-test", only=["jerry"], ledger_path=ledger)
    assert rerun == []


def test_bootstrap_reports_slack_error(tmp_path, monkeypatch):
    crew = load_config()
    ledger = tmp_path / "slack-apps.json"
    monkeypatch.setattr(
        slack_admin, "_post", lambda *a, **k: {"ok": False, "error": "token_expired"}
    )
    results = slack_admin.bootstrap(crew, "xoxe.xoxp-bad", only=["jerry"], ledger_path=ledger)
    assert len(results) == 1
    assert results[0].error == "token_expired"
    assert results[0].created is False
    assert not ledger.exists()  # nothing recorded on failure
