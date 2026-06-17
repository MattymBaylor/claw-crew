"""Command line entrypoint for the Open Claw crew.

    claw-crew list        # show the roster
    claw-crew doctor      # validate config + credentials, flag duplicates
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
