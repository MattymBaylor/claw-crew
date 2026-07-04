# Open Claw Crew Review — Approved Org & State of the System
**2026-07-04 · compiled by Cowork session · feeds the Claude Code CLI execution prompt**

---

## 1. Two systems, one cast (don't confuse them)

| | OpenClaw platform (legacy) | claw-crew (live Slack crew) |
|---|---|---|
| Where | VPS `/opt/openclaw` (+ old Mac install) | VPS `/opt/claw-crew` (Docker), repo `~/claw-crew` |
| What | Gateway + cron lanes, 16 agent defs | 17 Slack apps, one per agent, Socket Mode |
| Speaks in Slack as | single `@openclaw` gateway bot | individual bot users (@kramer, @jerry2, …) |
| Role source | `/opt/openclaw/state/agents/<name>/AGENTS.md` | `config/roster.yaml` (single source of truth) |
| Status | cron lanes half-broken (see §4) | 17/17 connected, healthy |

The org/roles "document" Matt remembered = the distributed per-agent AGENTS.md files on the VPS (pulled to `docs/archive/openclaw-org-pull.md`).

## 2. APPROVED org chart (18 — Whatley restored as VP Ops)

```
Matt (CEO)
└── Jerry — President & Coordinator          [@jerry2 · Sonnet-5]
    ├── VP MARKETING — Elaine                [@elaine2]
    │     ├── Bania — Graphic & Visual Design        [@bania2]
    │     ├── Peterman — Creative Production & Social [@peterman2]
    │     └── George — SEO & Analytics               [@george2]
    ├── VP OPERATIONS — Whatley (COO restored)  [NEW Slack app — tokens pending]
    │     ├── Kramer — n8n & Automation OWNER       [@kramer]
    │     ├── Morty — Infrastructure & IT            [@morty]
    │     ├── Newman — Watchdog & System Health      [@newman2]
    │     ├── Soup Nazi — Security                   [@soupnazi]
    │     ├── Mickey — QA & Test Automation          [@mickey2]
    │     └── Babu — Voice AI Quality Tester         [@babu2]
    ├── VP REVENUE — Frank — Sales & Outreach        [@frank2]
    │     ├── Puddy — Research & Intel (UNCHANGED — protect the working lane) [@puddy]
    │     └── Bookman — Deep-Dive Research           [@bookman2]
    └── Direct: Leo — Communications [@leo] · Jackie — Compliance [@jackie2] · Lloyd — Strategy [@lloyd2]
```

Decisions locked: legacy business roles restored (Sales, Voice QA, Watchdog, Design); Puddy stays Research (his intel lane is one of the few healthy crons — reports to Frank because intel feeds sales); Kramer explicitly owns n8n/automation (ownership, under VP Ops); **Whatley added back as VP Operations** — he never migrated to claw-crew (parked as `tim-watley.bak` during the Mac-era cleanup; 3rd most active legacy agent at 14.5MB). Hierarchy = 3 VPs under Jerry; Blake dropped.

Whatley goes live the moment his Slack app tokens land in `.env` (`claw-crew` skips uncredentialed agents cleanly until then — the crew directory lists him from day one so routing already knows the COO exists).

**Still deferred:** Crazy Joe Davola (traffic), Sue-Ellen (web dev).

## 3. Who's actually working (activity evidence)

**Legacy platform lifetime memory (sqlite size ≈ lifetime work):** Jerry/main **99MB**, Elaine **16MB**, Whatley **14.5MB**, Puddy **14MB**, Joe Davola 2MB — everyone else 69KB (baseline = never really worked). Most agent activity froze **Jun 17**; only `main` is active since.

**Cron lanes today (21 jobs):** OK = Joe Traffic, Jerry Facilitator, George Cost&Rev, Kramer Build, Puddy Morning Intel, Bania Design (+war-room-facilitator). **ERROR = 14 jobs** incl. Elaine Ship, Frank Sales, Peterman Creative, Puddy SaaS, Newman Watchdog, Mickey QA, all health checks + standup.

**claw-crew Slack bots:** 17/17 connected (restarted 09:03 today). Only `data/jerry.json` exists → only Jerry has held real Slack conversations so far; the other 16 are online but idle. #war-room ships are posted by the legacy `@openclaw` gateway (Bania Design Drop landed this morning), mention density there: Lloyd 81 · Jerry 57 · Newman 49 · Kramer 40 · Mickey 39 · Joe 35.

## 4. Issues log (found today — NOT in current scope, candidates for next prompt)

1. **14 cron jobs in ERROR** — mix of Slack delivery failure (`account_inactive` on C0ANVD9D1DJ announce lane) and lane-level errors. Newman's 00:27 watchdog + nightly note flag the same.
2. **Gemini embeddings 403 PERMISSION_DENIED** — OpenClaw memory sync failing every session start.
3. **Gateway startup storm** 00:15–00:19 UTC (`embeddedAgent` unrecognized key) — self-recovered 01:28; key still in config.
4. **agents/main/sessions = 1.2GB** (~17k files) — needs periodic cleanup.
5. **12 of 17 bots have suffixed handles** (@jerry2 …) — clean names squatted by the 14 dormant human accounts (overnight report Job 2). Deactivating those frees the names; bot usernames can then be reclaimed per app.
6. claw-crew log noise: unhandled `member_left_channel` events (cosmetic).
7. `openclaw wiki_*` tools exist but are stripped by the messaging tool-policy; no wiki dir found on disk — the real change journal = `state/workspace/memory/YYYY-MM-DD.md` + `logs/config-audit.jsonl`.

## 5. What ships next (via CLI prompt)

Crew-directory injection: every agent's system prompt gets an auto-generated roster block (real Slack IDs resolved at runtime via auth.test, "(you)" marker, reports_to lines, routing rules: only these 17 handles, never invent one, unsure → @jerry, n8n → @kramer). Built from roster.yaml at startup — edit the roster, directory updates itself. Plus the approved role/hierarchy updates to roster.yaml itself. Tests + deploy + verify included in the prompt.
