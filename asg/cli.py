#!/usr/bin/env python3
"""
ASG (Aldertech Storage Governor) — CLI entry point.

Usage:
    asg status                   Full status overview
    asg capacity                 Real capacity report
    asg scrub    [--dry-run]     Throttled scrub
    asg check                    Integrity check
    asg snapshot [--dry-run]     Pre-backup snapshot cycle
    asg cleanup  [--dry-run]     Clean up old snapshots only

All filesystem-modifying commands support --dry-run.
Pool UUID is validated before every operation.
"""

import argparse
import sys

from . import config
from .pool_validator import validate_pool, PoolValidationError
from .integrity_monitor import check_integrity, print_status as integrity_status
from .scrub_controller import run_scrub
from .capacity_engine import run_capacity_report
from .snapshot_bridge import (
    create_snapshot,
    cleanup_snapshots,
    list_snapshots,
    run_snapshot_cycle,
)


def cmd_scrub(args: argparse.Namespace) -> None:
    """Run a heuristic-throttled BTRFS scrub."""
    run_scrub(dry_run=args.dry_run)


def cmd_check(_args: argparse.Namespace) -> None:
    """Run RAID1 integrity check across all devices."""
    errors = check_integrity()
    if errors:
        sys.exit(1)


def cmd_capacity(_args: argparse.Namespace) -> None:
    """Print real capacity report with days-to-full prediction."""
    run_capacity_report()


def cmd_snapshot(args: argparse.Namespace) -> None:
    """Run the full snapshot lifecycle (cleanup + create)."""
    run_snapshot_cycle(dry_run=args.dry_run)


def cmd_cleanup(args: argparse.Namespace) -> None:
    """Clean up expired snapshots only."""
    cleanup_snapshots(dry_run=args.dry_run)


def cmd_status(_args: argparse.Namespace) -> None:
    """Full status overview: integrity + capacity + snapshots."""
    print("=" * 65)
    print("  ASG (Aldertech Storage Governor) — Status Overview")
    print("=" * 65)

    # Integrity
    print("\n--- Integrity ---")
    integrity_status()

    # Capacity
    print("\n--- Capacity ---")
    run_capacity_report()

    # Snapshots
    print("\n--- Snapshots ---")
    snaps = list_snapshots()
    if snaps:
        for s in snaps:
            age = s["timestamp"].strftime("%Y-%m-%d %H:%M:%S")
            print(f"  {s['name']}  (created: {age})")
    else:
        print("  No pre-backup snapshots found.")

    print("\n" + "=" * 65)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="asg",
        description="ASG (Aldertech Storage Governor)",
    )
    parser.add_argument("--config", help="Path to config YAML file")
    
    subparsers = parser.add_subparsers(dest="command", required=True)

    # status
    p_status = subparsers.add_parser("status", help="Full status overview")
    p_status.set_defaults(func=cmd_status)

    # capacity
    p_cap = subparsers.add_parser("capacity", help="Real capacity report")
    p_cap.set_defaults(func=cmd_capacity)

    # scrub
    p_scrub = subparsers.add_parser("scrub", help="Run throttled scrub")
    p_scrub.add_argument("--dry-run", action="store_true",
                         help="Simulate without modifying the filesystem")
    p_scrub.set_defaults(func=cmd_scrub)

    # check
    p_check = subparsers.add_parser("check", help="Run integrity check")
    p_check.set_defaults(func=cmd_check)

    # snapshot
    p_snap = subparsers.add_parser("snapshot", help="Pre-backup snapshot cycle")
    p_snap.add_argument("--dry-run", action="store_true",
                        help="Simulate without creating/deleting snapshots")
    p_snap.set_defaults(func=cmd_snapshot)

    # cleanup
    p_clean = subparsers.add_parser("cleanup", help="Clean up old snapshots")
    p_clean.add_argument("--dry-run", action="store_true",
                         help="Simulate without deleting snapshots")
    p_clean.set_defaults(func=cmd_cleanup)

    args = parser.parse_args()

    # Initialise config
    config.init(args.config)

    try:
        args.func(args)
    except PoolValidationError as exc:
        print(f"POOL VALIDATION FAILED: {exc}", file=sys.stderr)
        sys.exit(2)
    except KeyboardInterrupt:
        print("\nInterrupted.")
        sys.exit(130)


if __name__ == "__main__":
    main()
