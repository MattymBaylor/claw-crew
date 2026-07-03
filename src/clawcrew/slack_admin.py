"""Batch-create Slack apps from crew manifests via Slack's App Manifest API.

Standing up ~15 apps by hand is the tedious part. Slack's ``apps.manifest.create``
endpoint can create an app from a manifest programmatically, authenticated with
an *App Configuration Token* (generated at api.slack.com/apps -> "Your App
Configuration Tokens" -> Generate Token).

What this DOES automate: creating each app with the right name, scopes, events,
Messages tab, and Socket Mode. What it can NOT (Slack has no API for it):
installing the app to the workspace (mints the ``xoxb`` bot token) and generating
the ``xapp`` app-level token. Those two clicks per app stay manual.

Only the pure helpers (agent selection, ledger I/O) and the thin request wrapper
live here; the network call is isolated in ``_post`` so the logic is testable.
"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path

from .config import REPO_ROOT, AgentConfig, CrewConfig
from .manifest import build_manifest

SLACK_API = "https://slack.com/api"
# Records handle -> {app_id, name} for apps this tool created, so re-running is
# idempotent and never makes duplicate apps. Not secret, but environment-local.
LEDGER_PATH = REPO_ROOT / "slack-apps.json"


class SlackAdminError(RuntimeError):
    """Raised when Slack rejects a manifest/app request."""


@dataclass
class BootstrapResult:
    handle: str
    name: str
    created: bool = False
    app_id: str | None = None
    error: str | None = None
    skipped_reason: str | None = None


def load_ledger(path: Path = LEDGER_PATH) -> dict:
    if path.exists():
        return json.loads(path.read_text())
    return {}


def save_ledger(ledger: dict, path: Path = LEDGER_PATH) -> None:
    path.write_text(json.dumps(ledger, indent=2, sort_keys=True) + "\n")


def select_agents(
    crew: CrewConfig,
    ledger: dict,
    only: list[str] | None = None,
    skip: list[str] | None = None,
) -> list[AgentConfig]:
    """Agents that still need an app: honor --only/--skip and the ledger.

    An agent already recorded in the ledger is skipped so re-running never
    creates a duplicate app.
    """
    only_set = {h.lstrip("@") for h in only} if only else None
    skip_set = {h.lstrip("@") for h in skip} if skip else set()
    out: list[AgentConfig] = []
    for a in crew.agents:
        if only_set is not None and a.handle not in only_set:
            continue
        if a.handle in skip_set or a.handle in ledger:
            continue
        out.append(a)
    return out


def _post(method: str, token: str, params: dict) -> dict:
    data = dict(params)
    data["token"] = token
    body = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(f"{SLACK_API}/{method}", data=body)
    with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310 (fixed https host)
        return json.loads(resp.read().decode())


def create_app(access_token: str, agent: AgentConfig, crew: CrewConfig) -> str:
    """Create one Slack app from ``agent``'s manifest; return its app_id."""
    manifest = build_manifest(agent, crew)
    payload = _post("apps.manifest.create", access_token, {"manifest": json.dumps(manifest)})
    if not payload.get("ok"):
        raise SlackAdminError(payload.get("error", "unknown_error"))
    return payload["app_id"]


def bootstrap(
    crew: CrewConfig,
    access_token: str | None,
    *,
    only: list[str] | None = None,
    skip: list[str] | None = None,
    dry_run: bool = False,
    ledger_path: Path = LEDGER_PATH,
) -> list[BootstrapResult]:
    ledger = load_ledger(ledger_path)
    targets = select_agents(crew, ledger, only=only, skip=skip)
    results: list[BootstrapResult] = []
    for agent in targets:
        r = BootstrapResult(handle=agent.handle, name=agent.name)
        if dry_run:
            r.skipped_reason = "dry-run"
            results.append(r)
            continue
        try:
            r.app_id = create_app(access_token, agent, crew)
            r.created = True
            ledger[agent.handle] = {"app_id": r.app_id, "name": agent.name}
            save_ledger(ledger, ledger_path)
        except Exception as exc:  # keep going; report per-agent
            r.error = str(exc)
        results.append(r)
    return results
