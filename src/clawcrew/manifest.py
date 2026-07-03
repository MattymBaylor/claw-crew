"""Build Slack app manifests for the crew.

Every agent is its own Slack app. Standing up ~15 apps by hand is tedious, so
this module turns each roster entry into a Slack **app manifest** -- the exact
scopes/events from the README "Slack setup" section -- that can be pasted into
"Create New App -> From a manifest".

The functions here are PURE: they read only the dataclasses from ``config`` and
return plain dicts. Serialization (yaml/json) and I/O live in the CLI.
"""

from __future__ import annotations

from .config import AgentConfig, CrewConfig

# Bot token scopes -- mirrors README "Slack setup (per agent)".
BOT_SCOPES: tuple[str, ...] = (
    "app_mentions:read",
    "channels:read",
    "channels:join",
    "chat:write",
    "im:history",
    "im:read",
    "im:write",
    "users:read",
)

# Bot events the agents subscribe to (mentions in rooms + direct messages).
BOT_EVENTS: tuple[str, ...] = (
    "app_mention",
    "message.im",
)


def build_manifest(agent: AgentConfig, crew: CrewConfig) -> dict:
    """Return a Slack app manifest dict for a single agent.

    The manifest reflects what these agents actually need: app-mention/DM
    events over Socket Mode, plus the scopes to read channels, join them, post
    messages, and resolve user names. ``crew`` is accepted so the manifest can
    grow crew-aware fields later (e.g. a description) without a signature
    change.
    """
    return {
        "display_information": {
            "name": agent.name,
            "description": f"{agent.role} on {crew.name}".strip(),
        },
        "features": {
            "bot_user": {
                "display_name": agent.handle,
                "always_online": True,
            },
            # Turn ON the Messages tab so users can actually DM the bot.
            # Without this Slack shows "Sending messages to this app has been
            # turned off." home_tab off; messages tab on and writable.
            "app_home": {
                "home_tab_enabled": False,
                "messages_tab_enabled": True,
                "messages_tab_read_only_enabled": False,
            },
        },
        "oauth_config": {
            "scopes": {
                "bot": list(BOT_SCOPES),
            },
        },
        "settings": {
            "event_subscriptions": {
                "bot_events": list(BOT_EVENTS),
            },
            "interactivity": {
                "is_enabled": False,
            },
            "org_deploy_enabled": False,
            "socket_mode_enabled": True,
            "token_rotation_enabled": False,
        },
    }


def manifests_for_crew(crew: CrewConfig) -> dict[str, dict]:
    """Return ``{handle: manifest}`` for every agent in the crew."""
    return {agent.handle: build_manifest(agent, crew) for agent in crew.agents}
