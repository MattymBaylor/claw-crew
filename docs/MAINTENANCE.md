# Maintaining the Open Claw crew

This is the run-book for keeping the crew clean and connected. The goal: a
hands-off **midnight audit-and-heal** that keeps every agent on DMs, in the
shared rooms, and free of duplicates.

---

## The nightly job

`claw-crew nightly` does, in one run:

1. **Audit** (`doctor`) — flags duplicate names/handles (the "two Jerries"
   problem) and any agent missing Slack credentials.
2. **Heal** (`provision`) — for each agent: verifies its token authenticates,
   then joins every required room (`resources`, `huddle`) and every public
   channel it can see, **except the office**.

It exits non-zero if anything needs a human, so a scheduler can alert on it.

```bash
claw-crew nightly            # audit + heal
claw-crew nightly --dry-run  # show what it would do, change nothing
```

### Option A — plain cron (midnight)

```cron
# m h dom mon dow   command
0 0 * * *  cd /path/to/claw-crew && /usr/bin/env -S bash -lc 'set -a; . .env; set +a; claw-crew nightly' >> /var/log/claw-crew-nightly.log 2>&1
```

### Option B — Claude Code on the web (`/loop`)

If you run this from a Claude Code session, the `/loop` skill can re-run the
maintenance command on an interval, e.g. nightly:

```
/loop 24h claw-crew nightly
```

(Choose whichever the timer should live in — a real cron on a box is the more
durable home for a true midnight job.)

---

## Cleanup checklist (the "overhaul")

Run this when the roster feels messy:

1. `claw-crew doctor` → fix every `‼️` it prints.
   - **Duplicates** (two Jerries / floaters): delete the extra entry in
     `config/roster.yaml`. In Slack, deactivate/remove the duplicate app so the
     ghost stops appearing in rooms.
   - **Missing creds**: add the agent's `xoxb-`/`xapp-` tokens to `.env`.
2. `claw-crew provision --dry-run` → confirm the join plan looks right.
3. `claw-crew provision` → apply it.
4. Confirm avatars: every `assets/avatars/<handle>.png` exists and is uploaded
   to its Slack app (see `assets/avatars/README.md` for sizing).

The roster in `config/roster.yaml` is the single source of truth — fix things
there, not by hand in Slack, so the nightly job keeps them that way.

---

## Claude Code on the web — SessionStart hook

> ⚠️ The auto-mode classifier **blocked** me from writing these two files
> directly (they change the agent's startup config). They're provided here for
> you to add intentionally. Once they're on the default branch, every future web
> session installs deps automatically before running tests/linters.

Create `.claude/hooks/session-start.sh`:

```bash
#!/bin/bash
# SessionStart hook: install Python deps so tests/linters work in web sessions.
set -euo pipefail
cd "${CLAUDE_PROJECT_DIR:-.}"
python3 -m pip install --quiet --upgrade pip
python3 -m pip install --quiet -r requirements.txt
python3 -m pip install --quiet -e .
echo "claw-crew session hook: dependencies installed."
```

```bash
chmod +x .claude/hooks/session-start.sh
```

Create / merge `.claude/settings.json`:

```json
{
  "hooks": {
    "SessionStart": [
      { "hooks": [ { "type": "command", "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/session-start.sh" } ] }
    ]
  }
}
```

Validate it: `CLAUDE_CODE_REMOTE=true ./.claude/hooks/session-start.sh`

This hook runs **synchronously** (deps guaranteed ready before the session
starts; slightly slower startup). Switch to async mode if you prefer faster
startups and can tolerate a brief race before deps land.
