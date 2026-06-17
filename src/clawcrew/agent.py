"""A single Open Claw agent: a Slack (Socket Mode) app backed by Claude.

Each agent:
  * responds in DMs (so "everybody is on direct messages")
  * responds when @-mentioned in any channel it is in
  * can address crewmates by @-mentioning their handle
"""

from __future__ import annotations

import logging
import re

from .claude_client import ClaudeClient
from .config import AgentConfig, CrewConfig

log = logging.getLogger(__name__)

_MENTION_RE = re.compile(r"<@[A-Z0-9]+>")


def _strip_mentions(text: str) -> str:
    return _MENTION_RE.sub("", text or "").strip()


class ClawAgent:
    def __init__(self, agent: AgentConfig, crew: CrewConfig) -> None:
        self.agent = agent
        self.crew = crew
        self._app = None
        self._handler = None

    def _claude(self) -> ClaudeClient:
        return ClaudeClient(model=self.agent.model, max_tokens=self.agent.max_tokens)

    def build(self):
        from slack_bolt import App

        app = App(token=self.agent.bot_token)
        system_prompt = self.agent.rendered_system_prompt(self.crew.name)
        claude = self._claude()

        def respond(text: str, say) -> None:
            prompt = _strip_mentions(text)
            if not prompt:
                return
            try:
                say(claude.reply(system_prompt, prompt))
            except Exception as exc:  # surface failures into the thread, don't crash
                log.exception("%s failed to reply", self.agent.handle)
                say(f"({self.agent.name} hit an error: {exc})")

        @app.event("app_mention")
        def _on_mention(event, say):
            respond(event.get("text", ""), say)

        @app.event("message")
        def _on_message(event, say):
            # Only auto-reply to direct messages; channel chatter needs a mention.
            if event.get("channel_type") == "im" and not event.get("bot_id"):
                respond(event.get("text", ""), say)

        self._app = app
        return app

    def start(self) -> None:
        from slack_bolt.adapter.socket_mode import SocketModeHandler

        if self._app is None:
            self.build()
        self._handler = SocketModeHandler(self._app, self.agent.app_token)
        log.info("Starting agent %s", self.agent.handle)
        self._handler.start()
