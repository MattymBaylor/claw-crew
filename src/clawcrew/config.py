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


def data_dir() -> Path:
    """Directory where agents persist conversation memory.

    Defaults to ``<repo>/data`` and is overridable via ``CLAW_CREW_DATA_DIR`` so
    the container can point it at a mounted volume that survives rebuilds.
    """
    return Path(os.environ.get("CLAW_CREW_DATA_DIR") or (REPO_ROOT / "data"))


class ConfigError(ValueError):
    """Raised when the roster is missing required fields or is malformed."""


def _real_token(value: str | None) -> str | None:
    """Return a token only if it looks real.

    `.env.example` ships placeholder values like ``xoxb-...`` / ``xapp-...``.
    Copying it to `.env` would otherwise make every agent look credentialed, so
    treat any value that is empty or still carries the ``...`` placeholder
    marker as missing.
    """
    if not value or "..." in value:
        return None
    return value


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
    reports_to: str = ""

    @property
    def bot_token(self) -> str | None:
        return _real_token(os.environ.get(self.bot_token_env))

    @property
    def app_token(self) -> str | None:
        return _real_token(os.environ.get(self.app_token_env))

    @property
    def has_credentials(self) -> bool:
        return bool(self.bot_token and self.app_token)

    def rendered_system_prompt(self, crew_name: str, directory: str = "") -> str:
        """Render the prompt template; weave in the crew directory.

        If the template carries a ``{crew_directory}`` placeholder the block is
        substituted there; otherwise it is appended after the base prompt.
        """
        if "{crew_directory}" in self.system_prompt:
            return self.system_prompt.format(
                name=self.name,
                role=self.role,
                persona=self.persona,
                crew=crew_name,
                crew_directory=directory,
            ).strip()
        base = self.system_prompt.format(
            name=self.name, role=self.role, persona=self.persona, crew=crew_name
        )
        if directory:
            return f"{base.rstrip()}\n\n{directory.strip()}\n"
        return base


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

    def directory_block(
        self,
        viewer_handle: str | None = None,
        id_map: dict[str, str] | None = None,
    ) -> str:
        """Markdown crew directory injected into every agent's prompt.

        ``id_map`` maps handle -> Slack bot user id (resolved at startup via
        auth.test) so mentions actually ping; without it we fall back to plain
        ``@handle`` text. The viewer's own row is marked ``(you)``.
        """
        id_map = id_map or {}
        lines = ["## Crew directory", ""]
        for a in self.agents:
            uid = id_map.get(a.handle)
            mention = f"<@{uid}> (@{a.handle})" if uid else f"@{a.handle}"
            line = f"- {mention} — {a.name} — {a.role}"
            if a.reports_to:
                line += f" — reports to @{a.reports_to}"
            if viewer_handle and a.handle == viewer_handle:
                line += " (you)"
            lines.append(line)
        lines += [
            "",
            "Routing rules:",
            "- These are the ONLY crew members. Never invent or guess a handle.",
            "- Not sure who owns something? Ask @jerry to route it.",
            "- n8n / workflow automation questions go to @kramer.",
            "- Hand off work by @-mentioning the owner with a one-line brief.",
            "- Every project handoff or stage change ALSO gets reported to @davola",
            "  as: PROJECT | stage | owner — the log stamps the real time",
            "  automatically. NEVER guess or invent dates.",
            "Truth rules:",
            "- Posts from @openclaw are the legacy platform's scheduled lanes —",
            "  they are NOT your own actions or memories, even when they carry a",
            "  crew member's name.",
            "- Never claim memory of work you don't actually remember. If something",
            "  is attributed to you that you can't recall, say so plainly and point",
            "  to the Davola Log — playing along corrupts the record.",
        ]
        return "\n".join(lines)

    def system_prompt_for(
        self, agent: AgentConfig, id_map: dict[str, str] | None = None
    ) -> str:
        """Single entry point: agent prompt + crew directory."""
        return agent.rendered_system_prompt(
            self.name, directory=self.directory_block(agent.handle, id_map)
        )


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
                reports_to=str(item.get("reports_to", "") or ""),
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
