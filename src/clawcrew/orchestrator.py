"""Run the whole crew: one Socket Mode connection per agent, in threads."""

from __future__ import annotations

import logging
import threading

from .agent import ClawAgent
from .config import CrewConfig

log = logging.getLogger(__name__)


def run_crew(crew: CrewConfig) -> None:
    runnable = [a for a in crew.agents if a.has_credentials]
    skipped = [a.handle for a in crew.agents if not a.has_credentials]
    if skipped:
        log.warning("Skipping %d agent(s) without credentials: %s", len(skipped), skipped)
    if not runnable:
        raise SystemExit("No agents have credentials. Fill in .env and try again.")

    threads: list[threading.Thread] = []
    for agent in runnable:
        claw = ClawAgent(agent, crew)
        t = threading.Thread(target=claw.start, name=f"agent-{agent.handle}", daemon=True)
        t.start()
        threads.append(t)

    log.info("Started %d agent(s). Press Ctrl-C to stop.", len(threads))
    try:
        for t in threads:
            t.join()
    except KeyboardInterrupt:
        log.info("Shutting down crew.")
