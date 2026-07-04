# OpenClaw Org / Roles — Pull (2026-07-04)

**Source:** the org/roles definition is **distributed** across the OpenClaw platform's per-agent role files on the VPS: `/opt/openclaw/state/agents/<name>/AGENTS.md` (Crazy Joe Davola uses `agent.md`). Each has frontmatter (`name`, `title`, `reportsTo`) + "Role & Responsibilities" + "Who You Work With" sections. There is **no single org-chart file** — these files collectively ARE the org doc. (A more formal version may also exist in Google Drive — not yet checked; say the word.)

## Hierarchy (as defined by `reportsTo`)
- **`main` = "CEO, GrowthMindset AI"** — this is **Jerry** (session `agent:main`; every agent's `reportsTo: main`; George's file names "Jerry (main) — your boss").
- **Whatley = COO** (reports to main).
- **Crazy Joe Davola = Traffic Coordinator** — routing layer: Matt → Jerry → Joe → agents (from `workspace/AGENTS.md`).
- Everyone else reports to `main`. It's a **flat hub-and-spoke**, not a deep tree.

## Full roster pull (16 agents)
| OpenClaw agent | Title (role) | Reports to | In claw-crew roster? |
|---|---|---|---|
| main (**Jerry**) | CEO, GrowthMindset AI | — (top) | yes (as `jerry`, role "Coordinator") |
| whatley | Chief Operating Officer | main | **no — extra** |
| crazy-joe-davola | Traffic Coordinator | (routing) | **no — extra** |
| blake | AI Framework Consultant | main | **no — extra (Matt: drop)** |
| sue-ellen | Web Developer | main | **no — extra** |
| babu | Voice AI Quality Tester | main | yes (role "Data") ⚠️ |
| bania | Graphic Artist & Visual Designer | main | yes (role "Test Automation") ⚠️ |
| elaine | Content & Social Media Lead | main | yes (role "Docs") |
| frank | Sales & Outreach | main | yes (role "Ops") ⚠️ |
| george | Efficiency Monitor & SEO Strategist | main | yes (role "Analytics") |
| kramer | Ideas Guy & N8N Workflow Owner | main | yes (role "Discovery") |
| lloyd-braun | IT & Internal Infrastructure | main | yes (role "Strategy") ⚠️ |
| mickey | QA Agent | main | yes (role "Quality Control") |
| newman | Watchdog & System Health Monitor | main | yes (role "Integrations") ⚠️ |
| peterman | AI Creative Producer & Social Strategist | main | yes (role "Design") |
| puddy | Research Agent | main | yes (role "Engineering") ⚠️ |

## Deltas vs `~/claw-crew/config/roster.yaml` (the 17-role source of truth)

**A. OpenClaw-only (extras — not in claw-crew):** `whatley` (COO), `crazy-joe-davola` (Traffic Coordinator), `blake` (AI Framework Consultant — **drop**), `sue-ellen` (Web Developer).

**B. claw-crew-only (no OpenClaw agent):** `leo` (Communications), `bookman` (Research), `soupnazi` (Security), `morty` (Infrastructure), `jackie` (Compliance).

**C. Role CONFLICTS — same character, different job in each system (need your call):**
| Character | OpenClaw says | claw-crew roster says |
|---|---|---|
| **puddy** | Research Agent | Engineering |
| **newman** | Watchdog / System Health | Integrations |
| **lloyd** | IT & Internal Infrastructure | Strategy |
| **bania** | Graphic Artist / Visual Designer | Test Automation |
| **babu** | Voice AI Quality Tester | Data |
| **frank** | Sales & Outreach | Ops |

**D. Hierarchy gap:** `roster.yaml` has **no reporting structure** at all — no `reportsTo`, no CEO/COO/Traffic-Coordinator layer. OpenClaw has all of that.

## Open decisions (for Co-Work / your review)
1. Which extras to fold into claw-crew: keep Joe Davola (Traffic) / Whatley (COO) / Sue-Ellen (Web Dev)? (Blake = drop.)
2. Resolve the 6 role conflicts above — which system is the truth per character?
3. Add a `reportsTo` (and titles) field to `roster.yaml`, or keep it flat?

*(No changes applied. Awaiting your curated decisions before proposing the roster.yaml diff.)*
