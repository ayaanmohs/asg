"""
RAID Integrity Monitor — error watchdog for all pool drives.

Polls `btrfs device stats` and detects any non-zero error counters
(checksum, read, write, flush, generation). When errors are found,
sends a notification and tracks last-seen counts to avoid duplicates.
"""

import json
import os
import re
import subprocess
from datetime import datetime

from . import config
from .pool_validator import require_pool, get_pool_mount
from . import notifier


def _log(message: str) -> None:
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] integrity: {message}")


def _state_path() -> str:
    return os.path.join(config.get()["state_dir"], "state.json")


def _load_state() -> dict:
    path = _state_path()
    if os.path.exists(path):
        try:
            with open(path, "r") as fh:
                return json.load(fh)
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def _save_state(state: dict) -> None:
    path = _state_path()
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as fh:
            json.dump(state, fh, indent=2)
    except OSError as exc:
        _log(f"Failed to save state: {exc}")


def _run_device_stats() -> str | None:
    mount = get_pool_mount()
    try:
        result = subprocess.run(
            ["sudo", "btrfs", "device", "stats", mount],
            capture_output=True, text=True, timeout=15,
        )
        if result.returncode == 0:
            return result.stdout
    except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
        _log(f"Failed to run btrfs device stats: {exc}")
    return None


def _parse_device_stats(raw: str) -> dict[str, dict[str, int]]:
    stats: dict[str, dict[str, int]] = {}
    for line in raw.splitlines():
        match = re.fullmatch(r"\[(.+?)]\.\s*(\w+)\s+(\d+)", line.strip())
        if match:
            device = match.group(1)
            field = match.group(2)
            count = int(match.group(3))
            stats.setdefault(device, {})[field] = count
    return stats


def check_integrity() -> dict[str, dict[str, int]]:
    """
    Run a full integrity check against all pool devices.

    Returns a dict of devices with non-zero error counters (empty if healthy).
    """
    require_pool()

    raw = _run_device_stats()
    if raw is None:
        _log("ERROR: Could not retrieve device stats. Pool may be degraded.")
        return {}

    all_stats = _parse_device_stats(raw)
    errors: dict[str, dict[str, int]] = {}

    for device, counters in all_stats.items():
        non_zero = {k: v for k, v in counters.items() if v > 0}
        if non_zero:
            errors[device] = non_zero

    if not errors:
        _log("Integrity check passed. Zero errors across all devices.")
        return {}

    # Deduplicate against previous alerts
    state = _load_state()
    last_errors_str = state.get("last_integrity_errors", "")
    current_errors_str = json.dumps(errors, sort_keys=True)

    if current_errors_str != last_errors_str:
        lines = []
        for device, fields in sorted(errors.items()):
            for field, count in sorted(fields.items()):
                lines.append(f"  [{device}] {field}: {count}")

        body = (
            "BTRFS device error counters have changed on "
            f"`{get_pool_mount()}`:\n"
            + "\n".join(lines)
            + "\n\nImmediate investigation recommended.\n"
            f"Run: `sudo btrfs device stats {get_pool_mount()}`"
        )

        notifier.send("CRITICAL: Device Errors Detected", body, color=0xE74C3C)
        _log(f"ALERT: errors found on {len(errors)} device(s)")

        state["last_integrity_errors"] = current_errors_str
        state["last_integrity_alert_time"] = datetime.now().isoformat()
        _save_state(state)
    else:
        _log(
            f"Errors present on {len(errors)} device(s) but unchanged "
            "since last alert. No duplicate notification sent."
        )

    return errors


def print_status() -> None:
    """Print a human-readable integrity report to stdout."""
    require_pool()
    mount = get_pool_mount()

    raw = _run_device_stats()
    if raw is None:
        print("ERROR: Could not retrieve device stats.")
        return

    all_stats = _parse_device_stats(raw)
    print(f"BTRFS Integrity Report — {mount}")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("-" * 65)

    healthy = True
    for device in sorted(all_stats.keys()):
        counters = all_stats[device]
        non_zero = {k: v for k, v in counters.items() if v > 0}

        if non_zero:
            healthy = False
            status = "ERRORS DETECTED"
            detail = ", ".join(f"{k}={v}" for k, v in sorted(non_zero.items()))
        else:
            status = "OK"
            detail = "all counters zero"

        print(f"  {device}: {status} — {detail}")

    print("-" * 65)
    print(f"Overall: {'HEALTHY' if healthy else 'DEGRADED — see errors above'}")
