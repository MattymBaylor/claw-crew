"""Provision & heal the crew's Slack wiring.

Responsibilities:
  * make sure every agent is in the required rooms (resources, huddle, ...)
  * make sure every agent is in every public channel it can see (minus office)
  * verify each agent's credentials actually authenticate
  * report duplicate roster entries so they can be cleaned up

The channel-selection logic is a pure function (`channels_to_join`) so it can be
unit-tested without touching Slack.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .config import AgentConfig, CrewConfig


@dataclass
class ChannelInfo:
    id: str
    name: str
    is_member: bool = False


@dataclass
class AgentReport:
    handle: str
    authenticated: bool = False
    auth_error: str | None = None
    joined: list[str] = field(default_factory=list)
    already_member: list[str] = field(default_factory=list)
    failed: dict[str, str] = field(default_factory=dict)
    skipped_no_creds: bool = False

    @property
    def ok(self) -> bool:
        return self.skipped_no_creds is False and self.authenticated and not self.failed


def channels_to_join(
    channels: list[ChannelInfo],
    *,
    office_channel: str,
    allow_office_access: bool,
    required_channels: tuple[str, ...],
    join_all_public_channels: bool,
) -> list[ChannelInfo]:
    """Return the channels an agent should be a member of but currently is not.

    `required_channels` are always included (unless they ARE the office and
    access is denied). When `join_all_public_channels` is true, every visible
    channel is included except the office (unless office access is allowed).
    """
    office = office_channel.strip().lower()
    required = {c.strip().lower() for c in required_channels}
    wanted: list[ChannelInfo] = []

    for ch in channels:
        name = ch.name.strip().lower()
        is_office = bool(office) and name == office
        is_required = name in required

        if is_office and not allow_office_access and not is_required:
            continue
        if not (join_all_public_channels or is_required):
            continue
        if ch.is_member:
            continue
        wanted.append(ch)

    return wanted


def _list_channels(client) -> list[ChannelInfo]:
    channels: list[ChannelInfo] = []
    cursor = None
    while True:
        resp = client.conversations_list(
            types="public_channel",
            exclude_archived=True,
            limit=200,
            cursor=cursor,
        )
        for c in resp.get("channels", []):
            channels.append(
                ChannelInfo(id=c["id"], name=c["name"], is_member=c.get("is_member", False))
            )
        cursor = (resp.get("response_metadata") or {}).get("next_cursor")
        if not cursor:
            break
    return channels


def provision_agent(agent: AgentConfig, crew: CrewConfig, *, dry_run: bool = False) -> AgentReport:
    report = AgentReport(handle=agent.handle)

    if not agent.has_credentials:
        report.skipped_no_creds = True
        return report

    from slack_sdk import WebClient
    from slack_sdk.errors import SlackApiError

    client = WebClient(token=agent.bot_token)

    try:
        client.auth_test()
        report.authenticated = True
    except SlackApiError as e:
        report.auth_error = str(e)
        return report

    channels = _list_channels(client)
    targets = channels_to_join(
        channels,
        office_channel=crew.office_channel,
        allow_office_access=crew.allow_office_access,
        required_channels=crew.required_channels,
        join_all_public_channels=crew.join_all_public_channels,
    )
    report.already_member = [c.name for c in channels if c.is_member]

    for ch in targets:
        if dry_run:
            report.joined.append(ch.name)
            continue
        try:
            client.conversations_join(channel=ch.id)
            report.joined.append(ch.name)
        except SlackApiError as e:
            report.failed[ch.name] = str(e)

    return report


def provision_crew(crew: CrewConfig, *, dry_run: bool = False) -> list[AgentReport]:
    return [provision_agent(agent, crew, dry_run=dry_run) for agent in crew.agents]


def leave_channel(crew: CrewConfig, channel_name: str, *, dry_run: bool = False) -> list[str]:
    """Make every credentialed agent leave ``channel_name``. Returns handles that left.

    Used to evict the crew from a room they should not be in (e.g. the owner's
    office after it was joined under a wrong roster name).
    """
    from slack_sdk import WebClient
    from slack_sdk.errors import SlackApiError

    wanted = channel_name.lstrip("#").strip().lower()
    left: list[str] = []
    for agent in crew.agents:
        if not agent.has_credentials:
            continue
        client = WebClient(token=agent.bot_token)
        try:
            target = next(
                (c for c in _list_channels(client) if c.name.lower() == wanted and c.is_member),
                None,
            )
            if target is None:
                continue
            if not dry_run:
                client.conversations_leave(channel=target.id)
            left.append(agent.handle)
        except SlackApiError:
            continue
    return left
