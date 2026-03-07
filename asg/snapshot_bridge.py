"""
Atomic Snapshot/Backup Bridge — pre-backup BTRFS snapshots.

Creates read-only BTRFS snapshots immediately before backup software
runs, ensuring consistency. Manages snapshot lifecycle (creation and
cleanup of expired snapshots).
"""

import os
import re
import subprocess
from datetime import datetime, timedelta

from . import config
from .pool_validator import require_pool, get_pool_mount
from . import notifier


def _log(message: str) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] snapshot: {message}")


def _snapshot_name() -> str:
    return f"pre-backup-{datetime.now().strftime('%Y%m%d-%H%M%S')}"


def _parse_snapshot_timestamp(name: str) -> datetime | None:
    match = re.match(r"pre-backup-(\d{8}-\d{6})", name)
    if match:
        try:
            return datetime.strptime(match.group(1), "%Y%m%d-%H%M%S")
        except ValueError:
            pass
    return None


def list_snapshots() -> list[dict]:
    """List existing pre-backup snapshots."""
    cfg = config.get()
    snap_dir = cfg["snapshots"]["directory"]
    if not os.path.isdir(snap_dir):
        return []

    snapshots = []
    try:
        for entry in sorted(os.listdir(snap_dir)):
            ts = _parse_snapshot_timestamp(entry)
            if ts is not None:
                snapshots.append({
                    "name": entry,
                    "path": os.path.join(snap_dir, entry),
                    "timestamp": ts,
                })
    except OSError as exc:
        _log(f"Error listing snapshots: {exc}")

    return snapshots


def create_snapshot(dry_run: bool = False) -> str | None:
    """Create a read-only snapshot. Returns the path on success."""
    require_pool()
    cfg = config.get()
    mount = get_pool_mount()
    snap_dir = cfg["snapshots"]["directory"]
    snap_name = _snapshot_name()
    snap_path = os.path.join(snap_dir, snap_name)

    if not dry_run and not os.path.isdir(snap_dir):
        try:
            os.makedirs(snap_dir, exist_ok=True)
            _log(f"Created snapshot directory: {snap_dir}")
        except OSError as exc:
            _log(f"Failed to create snapshot directory: {exc}")
            return None

    cmd = ["sudo", "btrfs", "subvolume", "snapshot", "-r", mount, snap_path]

    if dry_run:
        _log(f"DRY RUN: would execute: {' '.join(cmd)}")
        return snap_path

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode == 0:
            _log(f"Snapshot created: {snap_path}")
            return snap_path
        else:
            _log(f"Snapshot creation failed: {result.stderr.strip()}")
            return None
    except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
        _log(f"Snapshot creation error: {exc}")
        return None


def cleanup_snapshots(dry_run: bool = False) -> int:
    """Remove snapshots older than the configured retention period."""
    require_pool()
    cfg = config.get()
    retention_days = cfg["snapshots"]["retention_days"]
    cutoff = datetime.now() - timedelta(days=retention_days)
    snapshots = list_snapshots()
    removed = 0

    for snap in snapshots:
        if snap["timestamp"] < cutoff:
            cmd = ["sudo", "btrfs", "subvolume", "delete", snap["path"]]

            if dry_run:
                _log(f"DRY RUN: would delete old snapshot: {snap['name']}")
                removed += 1
                continue

            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                if result.returncode == 0:
                    _log(f"Deleted old snapshot: {snap['name']}")
                    removed += 1
                else:
                    _log(f"Failed to delete {snap['name']}: {result.stderr.strip()}")
            except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
                _log(f"Error deleting {snap['name']}: {exc}")

    if removed > 0:
        _log(f"Cleaned up {removed} snapshot(s) older than {retention_days} days.")

    return removed


def run_snapshot_cycle(dry_run: bool = False) -> None:
    """Full snapshot lifecycle: clean up old snapshots, then create a new one."""
    _log("Starting snapshot cycle...")

    cleaned = cleanup_snapshots(dry_run=dry_run)
    snap_path = create_snapshot(dry_run=dry_run)

    if snap_path:
        msg = f"Snapshot cycle complete.\n**Created:** `{os.path.basename(snap_path)}`"
        if cleaned > 0:
            msg += f"\n**Cleaned up:** {cleaned} expired snapshot(s)"
        notifier.send("Snapshot Created", msg, color=0x2ECC71)
        _log(f"Snapshot cycle complete. Active snapshot: {snap_path}")
    else:
        if not dry_run:
            notifier.send(
                "CRITICAL: Snapshot Failed",
                "Snapshot cycle completed but snapshot creation failed.\n"
                "Check logs for details.",
                color=0xE74C3C,
            )
            _log("WARNING: Snapshot cycle completed but snapshot creation failed.")

    if cleaned > 0:
        _log(f"Removed {cleaned} expired snapshot(s) during this cycle.")
