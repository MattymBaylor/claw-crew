"""Load and validate the crew roster.

The roster (config/roster.yaml) is the single source of truth for who is in the
crew and which rooms they belong to. Secrets never live here -- the roster only
names the env vars that hold each agent's Slack tokens.
"""

from __future__ import annotations

import os
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ROSTER_PATH = REPO_ROOT / "config" / "roster.yaml"


class ConfigError(ValueError):
    """Raised when the roster is missing required fields or is malformed."""


@dataclass(frozen=True)
class AgentConfig:
    name: str
    handle: str
    role: str
    persona: str
    bot_token_env: str
    app_token_env: str
    model: str
    max_tokens: int
    system_prompt: str
    avatar: str = ""

    @property
    def bot_token(self) -> str | None:
        return os.environ.get(self.bot_token_env)

    @property
    def app_token(self) -> str | None:
        return os.environ.get(self.app_token_env)

    @property
    def has_credentials(self) -> bool:
        return bool(self.bot_token and self.app_token)

    def rendered_system_prompt(self, crew_name: str) -> str:
        return self.system_prompt.format(
            name=self.name, role=self.role, persona=self.persona, crew=crew_name
        )


@dataclass(frozen=True)
class CrewConfig:
    name: str
    office_channel: str
    allow_office_access: bool
    required_channels: tuple[str, ...]
    join_all_public_channels: bool
    agents: tuple[AgentConfig, ...] = field(default_factory=tuple)

    def duplicates(self) -> dict[str, list[str]]:
        """Return duplicate names/handles so the roster can be cleaned up.

        Keyed by 'name:<value>' or 'handle:<value>', each mapping to the list of
        agent handles that collide. Comparison is case-insensitive.
        """
        out: dict[str, list[str]] = {}
        for field_name in ("name", "handle"):
            seen = Counter(getattr(a, field_name).strip().lower() for a in self.agents)
            for value, count in seen.items():
                if count > 1:
                    members = [
                        a.handle
                        for a in self.agents
                        if getattr(a, field_name).strip().lower() == value
                    ]
                    out[f"{field_name}:{value}"] = members
        return out


def load_config(path: str | Path | None = None) -> CrewConfig:
    roster_path = Path(path) if path else DEFAULT_ROSTER_PATH
    if not roster_path.exists():
        raise ConfigError(f"Roster file not found: {roster_path}")

    raw = yaml.safe_load(roster_path.read_text()) or {}
    crew = raw.get("crew") or {}
    defaults = raw.get("defaults") or {}
    agents_raw = raw.get("agents") or []

    if not agents_raw:
        raise ConfigError("Roster has no agents. Add at least one under 'agents:'.")

    default_model = defaults.get("model", "claude-opus-4-8")
    default_max_tokens = int(defaults.get("max_tokens", 1024))
    default_prompt = defaults.get(
        "system_prompt", "You are {name}, a member of {crew}. Role: {role}. {persona}"
    )

    agents: list[AgentConfig] = []
    for i, item in enumerate(agents_raw):
        missing = [k for k in ("name", "handle", "role") if not item.get(k)]
        if missing:
            raise ConfigError(f"Agent #{i + 1} is missing required field(s): {missing}")
        handle = item["handle"]
        agents.append(
            AgentConfig(
                name=item["name"],
                handle=handle,
                role=item["role"],
                persona=item.get("persona", ""),
                bot_token_env=item.get("bot_token_env", f"{handle.upper()}_BOT_TOKEN"),
                app_token_env=item.get("app_token_env", f"{handle.upper()}_APP_TOKEN"),
                model=item.get("model", default_model),
                max_tokens=int(item.get("max_tokens", default_max_tokens)),
                system_prompt=item.get("system_prompt", default_prompt),
                avatar=item.get("avatar", f"assets/avatars/{handle}.png"),
            )
        )

    return CrewConfig(
        name=crew.get("name", "Open Claw"),
        office_channel=(crew.get("office_channel") or "").strip(),
        allow_office_access=bool(crew.get("allow_office_access", False)),
        required_channels=tuple(crew.get("required_channels") or ()),
        join_all_public_channels=bool(crew.get("join_all_public_channels", True)),
        agents=tuple(agents),
    )
