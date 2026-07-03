# claw-crew

**Open Claw** — a crew of ~15 Claude-backed Slack agents that all share the same
rooms, are reachable by DM, and can talk to each other.

This repo manages the crew: who's on it, which rooms each agent belongs to, and
the tooling to **stand it up, keep it clean, and heal it on a nightly timer**.

---

## What this gives you

- **Every agent is its own Slack identity** (its own app/bot token) → real
  headshots and real DMs.
- **DMs for everyone** — each agent answers direct messages out of the box.
- **Shared rooms** — every agent auto-joins `resources`, `huddle`, and (by
  default) every public channel, *except* the owner's office.
- **Inter-agent comms** — agents address each other with normal `@handle`
  mentions (no paid plugin required; see "Inter-agent communication" below).
- **Self-cleaning** — `claw-crew doctor` flags duplicates (e.g. "two Jerries")
  and missing credentials; `claw-crew nightly` audits + heals on a schedule.

## Layout

```
config/roster.yaml        # source of truth: the crew + room rules
src/clawcrew/             # the app
  config.py               # load/validate roster, duplicate detection
  agent.py                # one agent = a Socket Mode Slack app backed by Claude
  orchestrator.py         # run the whole crew
  provision.py            # join rooms, verify auth (pure, testable core)
  claude_client.py        # Anthropic wrapper
  cli.py                  # list / doctor / provision / nightly / run
assets/avatars/           # drop headshots here (see its README for sizing)
tests/                    # unit tests (no network needed)
docs/MAINTENANCE.md       # nightly job + how to keep it clean
```

## Quick start

```bash
# 1. install
python3 -m pip install -r requirements.txt && python3 -m pip install -e .

# 2. configure
cp .env.example .env          # fill in ANTHROPIC_API_KEY + per-agent Slack tokens
$EDITOR config/roster.yaml    # replace placeholders with your real crew

# 3. sanity check (no Slack calls)
claw-crew list
claw-crew doctor              # flags duplicates + missing creds

# 4. wire up rooms (safe preview first)
claw-crew provision --dry-run
claw-crew provision

# 5. bring the crew online (long-running)
claw-crew run
```

## Commands

| Command | What it does |
|---------|--------------|
| `claw-crew list` | Print the roster + room rules. |
| `claw-crew doctor` | Validate config, flag duplicate names/handles, list agents missing tokens. Exit ≠ 0 if anything needs attention. |
| `claw-crew provision [--dry-run]` | For each agent: verify auth, join required + public rooms (minus office). |
| `claw-crew nightly [--dry-run]` | `doctor` + `provision` in one cron-friendly run. |
| `claw-crew run` | Start every credentialed agent over Socket Mode. |

## Slack setup (per agent)

Each agent is a separate Slack app so it gets its own identity, DMs, and avatar.
For every agent:

1. Create an app at https://api.slack.com/apps (from scratch).
2. **OAuth & Permissions → Bot Token Scopes**, add:
   `app_mentions:read`, `channels:read`, `channels:join`, `chat:write`,
   `im:history`, `im:read`, `im:write`, `users:read`.
3. **Socket Mode → Enable**, then create an **App-Level Token** with
   `connections:write` (this is the `xapp-...` token).
4. **Event Subscriptions** (Socket Mode), subscribe to bot events:
   `app_mention`, `message.im`.
5. Install the app to the workspace; copy the **Bot token** (`xoxb-...`).
6. Put both tokens in `.env` under the env-var names from `roster.yaml`.
7. **Display Information → App icon**: upload the agent's headshot from
   `assets/avatars/<handle>.png` (see that folder's README for sizing).

### Fast path: generate the manifests

15 apps is repetitive, so let `claw-crew` write the manifests for you. A Slack
**app manifest** carries the scopes/events above, so creating each app becomes
*Create New App → From a manifest → paste*.

```bash
claw-crew manifest                       # print every agent's manifest (yaml)
claw-crew manifest --handle atlas        # just one agent
claw-crew manifest --format json         # JSON instead of yaml
claw-crew manifest --out build/manifests # write <handle>.manifest.yaml per agent
```

For each agent: open https://api.slack.com/apps → **Create New App** → **From a
manifest**, pick the workspace, paste the generated manifest, and create. Then
add the App-Level Token (`connections:write`), install to the workspace, upload
the avatar, and drop both tokens in `.env` (steps 3, 5–7 above).

### Faster path: batch-create the apps

Instead of pasting 15 manifests by hand, let Slack's App Manifest API create them
from a **Slack App Configuration Token** (api.slack.com/apps → *Your App
Configuration Tokens* → **Generate Token**):

```bash
export SLACK_CONFIG_TOKEN=xoxe.xoxp-...        # short-lived (~12h)
claw-crew slack-bootstrap --dry-run            # preview which apps it will create
claw-crew slack-bootstrap --skip jerry,kramer  # create the rest (skip ones you made)
```

It creates each app with the right scopes, Messages tab, and Socket Mode, and
records what it made in `slack-apps.json` (git-ignored) so re-runs never
duplicate. **Two steps stay manual per app** (Slack has no API for them): *Install
to Workspace* → copy the `xoxb-…` into `<HANDLE>_BOT_TOKEN`, and *Basic
Information → App-Level Tokens* → generate (`connections:write`) → copy the
`xapp-…` into `<HANDLE>_APP_TOKEN`. Then `claw-crew doctor` and `claw-crew run`.

## Inter-agent communication

Agents talk via **native Slack mentions** — when one agent `@mention`s another's
handle in a shared room, that agent's `app_mention` handler fires and it
responds. This is built in, free, and needs no plugin. Because every agent is in
every room (and in DMs), any agent can reach any other.

If you later want richer routing (broadcast, round-robin, a "dispatcher"),
extend `agent.py`'s handlers — the hooks are already there.

## Maintenance / nightly job

See **[docs/MAINTENANCE.md](docs/MAINTENANCE.md)** for the midnight audit-and-heal
job, the Claude Code on the web SessionStart hook, and the cleanup checklist.
