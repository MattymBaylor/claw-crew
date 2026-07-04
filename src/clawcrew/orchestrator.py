"""Run the whole crew: one Socket Mode connection per agent, in threads."""

from __future__ import annotations

import logging
import threading

from .agent import ClawAgent
from .config import CrewConfig

log = logging.getLogger(__name__)


def _resolve_bot_ids(agents) -> dict[str, str]:
    """Map handle -> Slack bot user id via auth.test (best effort).

    Slack usernames are suffixed in this workspace (@jerry2 ...), so the crew
    directory embeds real ``<@USERID>`` mentions; plain @handle is the
    fallback when a lookup fails.
    """
    ids: dict[str, str] = {}
    try:
        from slack_sdk import WebClient
    except ImportError:
        log.warning("slack_sdk unavailable; crew directory uses plain @handles")
        return ids
    for a in agents:
        try:
            ids[a.handle] = WebClient(token=a.bot_token).auth_test()["user_id"]
        except Exception as exc:  # noqa: BLE001 — never block startup on this
            log.warning("auth.test failed for %s: %s", a.handle, exc)
    return ids


def run_crew(crew: CrewConfig) -> None:
    runnable = [a for a in crew.agents if a.has_credentials]
    skipped = [a.handle for a in crew.agents if not a.has_credentials]
    if skipped:
        log.warning("Skipping %d agent(s) without credentials: %s", len(skipped), skipped)
    if not runnable:
        raise SystemExit("No agents have credentials. Fill in .env and try again.")

    id_map = _resolve_bot_ids(runnable)
    log.info("Resolved %d/%d bot user ids for the crew directory", len(id_map), len(runnable))

    threads: list[threading.Thread] = []
    for agent in runnable:
        claw = ClawAgent(agent, crew, id_map)
        t = threading.Thread(target=claw.start, name=f"agent-{agent.handle}", daemon=True)
        t.start()
        threads.append(t)

    log.info("Started %d agent(s). Press Ctrl-C to stop.", len(threads))
    try:
        for t in threads:
            t.join()
    except KeyboardInterrupt:
        log.info("Shutting down crew.")
