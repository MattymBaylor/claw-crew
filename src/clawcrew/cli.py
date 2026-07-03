"""Command line entrypoint for the Open Claw crew.

    claw-crew list        # show the roster
    claw-crew doctor      # validate config + credentials, flag duplicates
    claw-crew manifest    # emit Slack app manifest(s) for the crew
    claw-crew slack-bootstrap  # batch-create Slack apps from manifests
    claw-crew provision   # join required/public rooms for every agent
    claw-crew nightly     # cron-friendly audit + heal (doctor + provision)
    claw-crew run         # start every agent (Socket Mode, long-running)
"""

from __future__ import annotations

import argparse
import logging
import sys

from .config import CrewConfig, load_config
from .provision import provision_crew


def _print_roster(crew: CrewConfig) -> None:
    print(f"Crew: {crew.name}  ({len(crew.agents)} members)")
    print(f"Office channel: {crew.office_channel or '(none)'}  "
          f"(agents join it: {crew.allow_office_access})")
    print(f"Required rooms: {', '.join(crew.required_channels) or '(none)'}")
    print(f"Join all public channels: {crew.join_all_public_channels}")
    print("-" * 60)
    for a in crew.agents:
        creds = "creds OK" if a.has_credentials else "NO CREDS"
        print(f"  @{a.handle:<10} {a.name:<10} {a.role:<16} [{creds}]")


def _check_duplicates(crew: CrewConfig) -> int:
    dups = crew.duplicates()
    if not dups:
        print("✅ No duplicate roster entries.")
        return 0
    print("‼️  Duplicate roster entries found (clean these up):")
    for key, members in dups.items():
        kind, value = key.split(":", 1)
        print(f"   - duplicate {kind} '{value}': {', '.join('@' + m for m in members)}")
    return 1


def _check_credentials(crew: CrewConfig) -> int:
    missing = [a.handle for a in crew.agents if not a.has_credentials]
    if not missing:
        print(f"✅ All {len(crew.agents)} agents have Slack credentials.")
        return 0
    print(f"‼️  {len(missing)} agent(s) missing credentials (set their tokens in .env):")
    print("   " + ", ".join("@" + h for h in missing))
    return 1


def cmd_doctor(crew: CrewConfig) -> int:
    problems = 0
    problems += _check_duplicates(crew)
    problems += _check_credentials(crew)
    return 1 if problems else 0


def _dump_manifest(manifest: dict, fmt: str) -> str:
    if fmt == "json":
        import json

        return json.dumps(manifest, indent=2)
    import yaml

    return yaml.safe_dump(manifest, sort_keys=False, default_flow_style=False).rstrip("\n")


def cmd_manifest(crew: CrewConfig, handle: str | None, fmt: str, out: str | None) -> int:
    from pathlib import Path

    from .manifest import manifests_for_crew

    all_manifests = manifests_for_crew(crew)
    if handle:
        wanted = handle.lstrip("@")
        if wanted not in all_manifests:
            known = ", ".join("@" + h for h in all_manifests)
            print(f"‼️  Unknown handle '@{wanted}'. Known handles: {known}")
            return 1
        selected = {wanted: all_manifests[wanted]}
    else:
        selected = all_manifests

    ext = "json" if fmt == "json" else "yaml"

    if out:
        out_dir = Path(out)
        out_dir.mkdir(parents=True, exist_ok=True)
        for h, manifest in selected.items():
            dest = out_dir / f"{h}.manifest.{ext}"
            dest.write_text(_dump_manifest(manifest, fmt) + "\n")
            print(f"  ✅ wrote {dest}")
        return 0

    for i, (h, manifest) in enumerate(selected.items()):
        if i:
            print()
        print(f"# ===== @{h} (paste into Create New App -> From a manifest) =====")
        print(_dump_manifest(manifest, fmt))
    return 0


def cmd_slack_bootstrap(crew: CrewConfig, args) -> int:
    import os

    from .slack_admin import bootstrap

    token = os.environ.get("SLACK_CONFIG_TOKEN")
    only = args.only.split(",") if args.only else None
    skip = args.skip.split(",") if args.skip else None

    if not args.dry_run and not token:
        print("‼️  No SLACK_CONFIG_TOKEN set.")
        print("   Generate one at https://api.slack.com/apps -> 'Your App Configuration")
        print("   Tokens' -> Generate Token, then: export SLACK_CONFIG_TOKEN=xoxe.xoxp-...")
        print("   (Tip: run with --dry-run first to preview which apps would be created.)")
        return 1

    results = bootstrap(crew, token, only=only, skip=skip, dry_run=args.dry_run)
    if not results:
        print("Nothing to create — every selected agent already has an app (see slack-apps.json).")
        return 0

    created = 0
    failures = 0
    for r in results:
        if r.skipped_reason == "dry-run":
            print(f"  DRY-RUN: would create app for @{r.handle} ({r.name})")
            continue
        if r.error:
            print(f"  ‼️  @{r.handle:<10} failed: {r.error}")
            failures += 1
            continue
        created += 1
        print(f"  ✅ @{r.handle:<10} created {r.app_id}  "
              f"-> https://api.slack.com/apps/{r.app_id}")

    if created:
        print("\nFor each app just created, two manual steps remain (Slack has no API):")
        print("  1. Install App -> Install to Workspace  -> copy xoxb-... into <HANDLE>_BOT_TOKEN")
        print("  2. Basic Information -> App-Level Tokens -> Generate (connections:write)")
        print("     -> copy xapp-... into <HANDLE>_APP_TOKEN")
        print("  Then: claw-crew doctor  (confirms creds)  and  claw-crew run")
    return 1 if failures else 0


def cmd_provision(crew: CrewConfig, dry_run: bool) -> int:
    reports = provision_crew(crew, dry_run=dry_run)
    label = "DRY-RUN: would join" if dry_run else "joined"
    failures = 0
    for r in reports:
        if r.skipped_no_creds:
            print(f"  @{r.handle:<10} skipped (no credentials)")
            continue
        if not r.authenticated:
            print(f"  @{r.handle:<10} ‼️  auth failed: {r.auth_error}")
            failures += 1
            continue
        status = "✅" if r.ok else "‼️ "
        print(f"  {status} @{r.handle:<10} {label} {len(r.joined)} room(s); "
              f"already in {len(r.already_member)}")
        for room, err in r.failed.items():
            print(f"        failed to join #{room}: {err}")
            failures += 1
    return 1 if failures else 0


def cmd_nightly(crew: CrewConfig, dry_run: bool) -> int:
    """Audit + heal in one shot. Designed to be safe to run on a cron timer."""
    print("=== Open Claw nightly maintenance ===")
    rc = 0
    print("\n[1/2] Roster audit")
    rc |= cmd_doctor(crew)
    print("\n[2/2] Room provisioning")
    rc |= cmd_provision(crew, dry_run=dry_run)
    print("\nDone.", "Issues need attention." if rc else "All healthy.")
    return rc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="claw-crew", description="Open Claw crew manager")
    parser.add_argument("-c", "--config", help="Path to roster.yaml")
    parser.add_argument("-v", "--verbose", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="Show the roster")
    sub.add_parser("doctor", help="Validate config + credentials, flag duplicates")
    p_man = sub.add_parser("manifest", help="Emit Slack app manifest(s) for the crew")
    p_man.add_argument("--handle", help="Only this agent's handle (default: all agents)")
    p_man.add_argument(
        "--format", choices=("yaml", "json"), default="yaml", help="Output format (default: yaml)"
    )
    p_man.add_argument("--out", help="Write one file per agent into this directory")
    p_boot = sub.add_parser("slack-bootstrap", help="Batch-create Slack apps from manifests")
    p_boot.add_argument("--only", help="Comma-separated handles to create (default: all remaining)")
    p_boot.add_argument("--skip", help="Comma-separated handles to skip (e.g. jerry,kramer)")
    p_boot.add_argument("--dry-run", action="store_true", help="Preview without creating apps")
    p_prov = sub.add_parser("provision", help="Join required/public rooms")
    p_prov.add_argument("--dry-run", action="store_true", help="Show actions without making them")
    p_night = sub.add_parser("nightly", help="Cron-friendly audit + heal")
    p_night.add_argument("--dry-run", action="store_true")
    sub.add_parser("run", help="Start every agent (long-running)")

    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    crew = load_config(args.config)

    if args.command == "list":
        _print_roster(crew)
        return 0
    if args.command == "doctor":
        return cmd_doctor(crew)
    if args.command == "manifest":
        return cmd_manifest(crew, handle=args.handle, fmt=args.format, out=args.out)
    if args.command == "slack-bootstrap":
        return cmd_slack_bootstrap(crew, args)
    if args.command == "provision":
        return cmd_provision(crew, dry_run=args.dry_run)
    if args.command == "nightly":
        return cmd_nightly(crew, dry_run=args.dry_run)
    if args.command == "run":
        from .orchestrator import run_crew

        run_crew(crew)
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
