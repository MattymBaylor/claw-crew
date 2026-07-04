# Open Claw — System State & Handoff

_Last updated: 2026-07-04. Read this BEFORE changing anything. The decisions
below were made deliberately by Matt (owner) — do not undo them without asking
him explicitly._

## The big picture: TWO separate systems, one Slack workspace

The Slack workspace (**Growthmindset**) contains exactly:
**1 human** (Matt Martelli, Primary Workspace Owner) + **19 crew bot apps**
(incl. Whatley + Davola, added 2026-07-04 PM) + **1 OpenClaw Gateway app**
(+ pre-existing Claude & Notion apps). Nothing else should be a member. 14 old
character-named USER accounts (Jerry Seinfeld, Cosmo Kramer, etc.) were
deliberately **deactivated** — do not reactivate or re-invite them.

### System 1 — OpenClaw platform (the original, ~6 months of work)
- Runs 24/7 in Docker on the Hostinger VPS `root@187.124.225.103`, project at
  `/opt/openclaw`, container `openclaw-openclaw-1`, behind Traefik.
- Its data/brain lives in `/opt/openclaw/state` (mounted as `/root/.openclaw`).
  **NEVER delete, rebuild, or bulk-edit this directory.** Backups exist
  (`*.bak.jul4*`, `openclaw.json.last-good`, rollback image
  `openclaw-openclaw:rollback-2026.5.12`).
- Dockerfile is **pinned to openclaw 2026.6.8** to match the config schema.
  Do not downgrade; upgrades (e.g. 2026.6.11) only as a planned change —
  they can trigger config migrations.
- Slack: connects via the **"OpenClaw Gateway" app (App ID A0BF78A8DM2)** —
  created fresh on 2026-07-04 after the original app was lost. Token rotation
  is done server-side via `/opt/openclaw/update-slack-tokens.sh` (silent
  prompts; secrets never go through chat). Manifest saved at
  `/opt/openclaw/slack-app-manifest.yaml`.
- Anthropic billing: uses key ending **a6AAA** (`openclaw-vps2`, funded
  account, auto-reload on). The old key (…98WQAA) was from a different,
  unfunded account — do not restore it.
- **Cron diet applied** (deliberate cost cut): Newman Watchdog, Joe Davola
  Traffic, and Mickey QA run ONCE DAILY (7:00/7:20/7:40 ET, was every few
  minutes); 7 routine monitoring lanes use claude-haiku-4-5. Managed via the
  `openclaw cron` CLI (the JSON cron store is migrated/stale — don't edit it
  directly). Do not re-accelerate these without Matt's OK.

### System 2 — claw-crew (the Seinfeld crew, built 2026-07-03/04)
- Repo: `github.com/MattymBaylor/claw-crew`, **`main` is the source of
  truth** — all work merged (PRs #1–#9 + the 2026-07-04 PM org/branch
  reconciliation), 52 tests green.
- Runs 24/7 as its own Docker container on the SAME VPS, project at
  `/opt/claw-crew` (separate compose project — do not merge it into
  /opt/openclaw's compose).
- **19 agents**, each its own Slack Socket Mode app with its own
  `xoxb-`/`xapp-` tokens in `/opt/claw-crew/.env` (and Matt's Mac at
  `~/claw-crew/.env`). `.env` files are gitignored — never commit or print.
- Roster/source of truth: `config/roster.yaml` — 19 members with Matt's
  APPROVED ORG CHART (2026-07-04, via `reports_to`): **Jerry = President &
  Coordinator**; VPs: **Elaine (Marketing)**, **Whatley (Operations)**,
  **Frank (Revenue)**. Notable: **Kramer = n8n, Automation & AI Frameworks
  Owner** (inherited Blake's AI-framework playbook; Blake's IT half went to
  Morty — full archive in `docs/blake-knowledge.md`), Bania = Graphic &
  Visual Design, Mickey = QA & Test Automation, Puddy = Research & Intel
  (deliberately unchanged lane), Davola = Traffic Coordinator (project-log
  protocol: every handoff reports "PROJECT | stage | owner | timestamp" to
  @davola — baked into every agent's directory routing rules; master log =
  Matt's traffic-log Google Sheet), **Morty =
  Infrastructure, IT & Web Development** (web/HTML/Python capability lives
  with him). Gap closure approved 2026-07-04 PM: Leo = Communications &
  Customer Success, Elaine adds Paid Acquisition, George adds Finance
  Tracking, Kramer adds Voice Agent Builds (Babu keeps QA). Sue-Ellen is
  BENCHED (web dev asks → @morty until she's activated). Do not change roles
  or hierarchy without Matt.

## Deliberate design decisions — DO NOT UNDO

1. **Models (cost):** crew default is `claude-haiku-4-5-20251001`; only jerry
   runs `claude-sonnet-5`. This was a ~30x API cost cut. Do not put the crew
   back on Opus.
2. **Bot-loop guard:** agents ignore ALL bot-authored messages (bot_id /
   bot_message). Prevents credit-burning loops with the gateway. Keep it.
3. **Office privacy:** `office_channel: "matts-office"` — the crew must NOT
   be in that channel. They were evicted manually; `claw-crew leave` exists
   for future evictions (needs `channels:manage`, which only newly generated
   apps have).
4. **Persistent memory:** each agent persists conversation history to
   `data/<handle>.json` (bounded, 12 turns/key; `CLAW_CREW_DATA_DIR` points
   at a Docker volume on the VPS). Threads inherit parent-channel history.
5. **Crew directory in prompts (v2, 2026-07-04 PM):** every agent's system
   prompt lists all 19 handles/roles **plus reports_to lines**, with real
   Slack user IDs resolved at startup via auth.test (mentions ping despite
   suffixed usernames) and a "never invent names" rule
   (`CrewConfig.directory_block` / `system_prompt_for`). Verified live:
   Jerry routes n8n→@kramer, graphics→@bania, traffic→@davola. Do not revert
   to the 17-agent flat version. Standing fact: Matt Martelli is the
   boss/CEO.
6. **Slack app manifests** (`claw-crew manifest` / `slack-bootstrap`) include
   the Messages tab (DM-ability), Socket Mode, and `channels:manage`. The
   ledger `slack-apps.json` (local, gitignored) prevents duplicate app
   creation — clear an entry only if the app truly doesn't exist.
7. **Anthropic keys are split on purpose** (usage visibility): crew uses the
   "new open claw" key (…ugAA); platform uses `openclaw-vps2` (…a6AAA).

## Operations quick reference

- Crew (VPS): `cd /opt/claw-crew && docker compose ...` (logs/restart/rebuild).
  `/opt/claw-crew` is **rsync-managed (no .git)**. Deploy = merge to `main`,
  then `rsync -az --exclude .git --exclude .env --exclude data
  --exclude OVERNIGHT_REPORT.md ~/claw-crew/ root@VPS:/opt/claw-crew/` and
  `docker compose up -d --build`. Never rsync/overwrite `.env` or `data/`.
  Content == `main` as of 2026-07-04 PM.
- Crew CLI: `claw-crew list | doctor | manifest | slack-bootstrap | provision
  | leave | nightly | run` (env from `.env` first).
- Platform: `docker logs openclaw-openclaw-1`, config via its own CLI, state
  in `/opt/openclaw/state`.
- Nightly maintenance: `claw-crew nightly` (audit + heal) runs from cron on
  the VPS at midnight.

## Known open items (safe to pick up)

- ~~Rebuild the crew container for the crew directory~~ **DONE 2026-07-04 PM**
  (enhanced v2 directory live, 19/19 agents, verified via live routing tests).
- ~~Locate the original org/roles document and fold hierarchy into
  roster.yaml~~ **DONE 2026-07-04 PM** — it was distributed across
  `/opt/openclaw/state/agents/<name>/AGENTS.md` (pull archived at
  `docs/archive/openclaw-org-pull.md`); Matt approved the 3-VP org, now in
  `roster.yaml` via `reports_to` (decision sheet: `docs/archive/crew-review-2026-07-04.md`).
- 3 flagged platform crons (Jerry Facilitator 2h → daily, disable malformed
  war-room-facilitator, fix "8AM Standup" timezone) — decisions approved by
  Matt, may or may not be applied yet.
- Point `/opt/claw-crew` at `main` tracking (content already identical).
- Optional: delete unused Anthropic API keys in the funded account.

## History (what happened, short)

2026-07-03/04 marathon: built the 17-agent crew from an empty repo (PR #1),
gave it personalities, avatars, and rooms; discovered the original OpenClaw
platform on the VPS broken by billing (wrong Anthropic account) + a dead
Slack app; fixed billing with a funded key, rebuilt the image to match the
config version (2026.6.8), created the new Gateway Slack app; deleted stray
duplicates ("two Jerries", Demo App, boring_bell container); deactivated 14
ghost user accounts; moved the crew to the VPS; added loop guard, persistent
memory, crew directory; cut models to Haiku and crons to daily.
