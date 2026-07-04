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
from .config import AgentConfig, CrewConfig, data_dir
from .memory import ConversationStore

log = logging.getLogger(__name__)

_MENTION_RE = re.compile(r"<@[A-Z0-9]+>")


def _strip_mentions(text: str) -> str:
    return _MENTION_RE.sub("", text or "").strip()


def _conversation_key(event: dict) -> str:
    """Derive the *write* key for a Slack event (where new turns are stored).

    Keyed by channel id, and further scoped by thread timestamp when the message
    lives in a thread so each thread keeps its own context.
    """
    channel = event.get("channel", "")
    thread_ts = event.get("thread_ts")
    return f"{channel}:{thread_ts}" if thread_ts else channel


def _history_keys(event: dict) -> list[str]:
    """Ordered keys whose history feeds a reply, parent scope first.

    A threaded message inherits the parent channel's history as a base, then its
    own thread turns: ``[channel, channel:thread_ts]``. A non-threaded message
    just reads the channel/DM key.
    """
    channel = event.get("channel", "")
    thread_ts = event.get("thread_ts")
    if thread_ts:
        return [channel, f"{channel}:{thread_ts}"]
    return [channel]


class ClawAgent:
    def __init__(
        self,
        agent: AgentConfig,
        crew: CrewConfig,
        id_map: dict[str, str] | None = None,
    ) -> None:
        self.agent = agent
        self.crew = crew
        self.id_map = id_map or {}
        # Persist this agent's memory to its own JSON file so it survives
        # restarts; the directory is a mounted volume on the VPS.
        self.memory = ConversationStore(path=data_dir() / f"{agent.handle}.json")
        self._app = None
        self._handler = None

    def _claude(self) -> ClaudeClient:
        return ClaudeClient(model=self.agent.model, max_tokens=self.agent.max_tokens)

    def build(self):
        from slack_bolt import App

        app = App(token=self.agent.bot_token)
        system_prompt = self.crew.system_prompt_for(self.agent, self.id_map)
        claude = self._claude()

        def respond(event: dict, say) -> None:
            # Never engage with bot-authored messages. The whole crew plus the
            # OpenClaw gateway share every room, so bot-to-bot replies can
            # cascade into mention loops that burn API credits.
            if event.get("bot_id") or event.get("subtype") == "bot_message":
                return
            prompt = _strip_mentions(event.get("text", ""))
            if not prompt:
                return
            key = _conversation_key(event)
            history = self.memory.history_for(_history_keys(event))
            try:
                answer = claude.reply(system_prompt, prompt, history=history)
            except Exception as exc:  # surface failures into the thread, don't crash
                log.exception("%s failed to reply", self.agent.handle)
                say(f"({self.agent.name} hit an error: {exc})")
                return
            # Only remember exchanges that actually completed. New turns are
            # written to the specific (thread-scoped) key; reads above inherit
            # the parent channel's history too.
            self.memory.add(key, "user", prompt)
            self.memory.add(key, "assistant", answer)
            say(answer)

        @app.event("app_mention")
        def _on_mention(event, say):
            respond(event, say)

        @app.event("message")
        def _on_message(event, say):
            # Only auto-reply to direct messages; channel chatter needs a
            # mention. Bot-authored traffic is filtered inside respond().
            if event.get("channel_type") == "im":
                respond(event, say)

        self._app = app
        return app

    def start(self) -> None:
        from slack_bolt.adapter.socket_mode import SocketModeHandler

        if self._app is None:
            self.build()
        self._handler = SocketModeHandler(self._app, self.agent.app_token)
        log.info("Starting agent %s", self.agent.handle)
        self._handler.start()
