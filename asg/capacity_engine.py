"""
Mismatched-Drive Capacity Engine — real free space and chunk analysis.

Standard `df -h` is mathematically incorrect for RAID1 with mismatched
drives. This module uses `btrfs filesystem usage` to calculate:

  1. Real free space accounting for the RAID1 pairing constraint.
  2. Chunk allocation status per device — warns on dangerous concentration.
  3. Days-to-full prediction from historical capacity data.
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
    print(f"[{timestamp}] capacity: {message}")


# ── Parsing helpers ──────────────────────────────────────────────────

def _parse_size(size_str: str) -> float:
    """
    Parse a human-readable BTRFS size string into GiB.

    Handles: "103.00GiB", "1.82TiB", "8.00MiB", "16.00KiB", "0.00B"
    """
    size_str = size_str.strip()
    if size_str == "-":
        return 0.0

    # Ordered longest-suffix-first to avoid "GiB" matching the "B" rule
    multipliers = [
        ("TiB", 1024.0),
        ("GiB", 1.0),
        ("MiB", 1 / 1024),
        ("KiB", 1 / (1024 ** 2)),
        ("B", 1 / (1024 ** 3)),
    ]

    for suffix, mult in multipliers:
        if size_str.endswith(suffix):
            try:
                return float(size_str[: -len(suffix)]) * mult
            except ValueError:
                return 0.0

    return 0.0


def _run_usage_tabular() -> str | None:
    mount = get_pool_mount()
    try:
        result = subprocess.run(
            ["sudo", "btrfs", "filesystem", "usage", "-T", mount],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode == 0:
            return result.stdout
    except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
        _log(f"Failed to get filesystem usage: {exc}")
    return None


def _run_usage_overview() -> str | None:
    mount = get_pool_mount()
    try:
        result = subprocess.run(
            ["sudo", "btrfs", "filesystem", "usage", mount],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode == 0:
            return result.stdout
    except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
        _log(f"Failed to get filesystem usage: {exc}")
    return None


# ── Core analysis ────────────────────────────────────────────────────

def parse_usage() -> dict | None:
    """Parse full BTRFS usage into a structured dict."""
    overview = _run_usage_overview()
    tabular = _run_usage_tabular()

    if not overview or not tabular:
        return None

    result: dict = {"overall": {}, "data_chunks": {}, "metadata_chunks": {},
                    "per_device": {}, "metadata_device_count": 0}

    for line in overview.splitlines():
        line = line.strip()
        if line.startswith("Device size:"):
            result["overall"]["device_size_gib"] = _parse_size(line.split(":", 1)[1])
        elif line.startswith("Device allocated:"):
            result["overall"]["allocated_gib"] = _parse_size(line.split(":", 1)[1])
        elif line.startswith("Device unallocated:"):
            result["overall"]["unallocated_gib"] = _parse_size(line.split(":", 1)[1])
        elif line.startswith("Used:"):
            result["overall"]["used_gib"] = _parse_size(line.split(":", 1)[1])
        elif line.startswith("Free (estimated):"):
            val = line.split(":", 1)[1].split("(")[0]
            result["overall"]["free_estimated_gib"] = _parse_size(val)
        elif line.startswith("Data ratio:"):
            try:
                result["overall"]["data_ratio"] = float(line.split(":", 1)[1].strip())
            except ValueError:
                result["overall"]["data_ratio"] = 2.0
        elif line.startswith("Metadata ratio:"):
            try:
                result["overall"]["metadata_ratio"] = float(line.split(":", 1)[1].strip())
            except ValueError:
                result["overall"]["metadata_ratio"] = 2.0

    for line in overview.splitlines():
        line = line.strip()
        chunk_match = re.match(
            r"(Data|Metadata),RAID1[^:]*:\s+Size:(\S+),\s+Used:(\S+)\s+\(([0-9.]+)%\)",
            line,
        )
        if chunk_match:
            chunk_type = chunk_match.group(1).lower()
            key = f"{chunk_type}_chunks"
            result[key] = {
                "total_gib": _parse_size(chunk_match.group(2)),
                "used_gib": _parse_size(chunk_match.group(3)),
                "used_pct": float(chunk_match.group(4)),
            }

    in_table = False
    for line in tabular.splitlines():
        line = line.strip()
        if line.startswith("Id Path"):
            in_table = True
            continue
        if line.startswith("-- ------"):
            if in_table:
                continue
            in_table = False
            continue
        if line.startswith("Total") or line.startswith("Used"):
            continue

        if in_table and line and line[0].isdigit():
            parts = line.split()
            if len(parts) >= 7:
                dev_path = parts[1]
                result["per_device"][dev_path] = {
                    "data_gib": round(_parse_size(parts[2]), 3),
                    "metadata_gib": round(_parse_size(parts[3]), 3),
                    "system_gib": round(_parse_size(parts[4]), 3),
                    "unallocated_gib": round(_parse_size(parts[5]), 3),
                    "total_gib": round(_parse_size(parts[6]), 3),
                }

    meta_count = sum(
        1 for d in result["per_device"].values() if d["metadata_gib"] > 0
    )
    result["metadata_device_count"] = meta_count

    return result


def calculate_real_free_space(usage: dict) -> dict:
    """
    Calculate real usable free space for a RAID1 pool with mismatched drives.

    RAID1 mirrors each chunk across two devices. The theoretical maximum
    usable space is:

        usable = min(sum_of_all / 2, sum_of_all - largest_drive)

    The second term accounts for the fact that the largest drive can only
    mirror data that fits on some other drive. For matched drives, both
    terms are equal. For mismatched drives, the second term may be smaller.
    """
    devices = usage.get("per_device", {})
    if not devices:
        return {"usable_ceiling_gib": 0, "real_free_gib": 0, "pct_used": 0}

    total_raw_gib = sum(d["total_gib"] for d in devices.values())
    largest_gib = max(d["total_gib"] for d in devices.values())

    raid1_half = total_raw_gib / 2.0
    pair_limit = total_raw_gib - largest_gib
    usable_ceiling = min(raid1_half, pair_limit)

    data_used = usage.get("data_chunks", {}).get("used_gib", 0)
    meta_used = usage.get("metadata_chunks", {}).get("used_gib", 0)
    total_used = data_used + meta_used

    real_free = max(0, usable_ceiling - total_used)
    pct_used = (total_used / usable_ceiling * 100.0) if usable_ceiling > 0 else 100.0

    return {
        "total_raw_gib": round(total_raw_gib, 2),
        "largest_device_gib": round(largest_gib, 2),
        "usable_ceiling_gib": round(usable_ceiling, 2),
        "data_used_gib": round(data_used, 2),
        "metadata_used_gib": round(meta_used, 2),
        "total_used_gib": round(total_used, 2),
        "real_free_gib": round(real_free, 2),
        "pct_used": round(pct_used, 1),
    }


def check_metadata_concentration(usage: dict) -> list[str]:
    """Check if metadata/system chunks are dangerously concentrated."""
    cfg = config.get()
    min_count = cfg["capacity"]["metadata_min_device_count"]
    warnings: list[str] = []

    meta_count = usage.get("metadata_device_count", 0)
    if meta_count < min_count:
        meta_devices = [
            path for path, d in usage.get("per_device", {}).items()
            if d["metadata_gib"] > 0
        ]
        warnings.append(
            f"Metadata is concentrated on only {meta_count} device(s): "
            f"{', '.join(meta_devices)}. "
            f"Threshold requires {min_count}+. "
            "Loss of any metadata device would make the pool unrecoverable."
        )

    sys_devices = [
        path for path, d in usage.get("per_device", {}).items()
        if d.get("system_gib", 0) > 0
    ]
    if len(sys_devices) < min_count:
        warnings.append(
            f"System chunks are concentrated on only {len(sys_devices)} device(s): "
            f"{', '.join(sys_devices)}."
        )

    return warnings


# ── Historical tracking & prediction ────────────────────────────────

def _history_path() -> str:
    return os.path.join(config.get()["state_dir"], "capacity_history.json")


def _load_history() -> list[dict]:
    path = _history_path()
    if os.path.exists(path):
        try:
            with open(path, "r") as fh:
                return json.load(fh)
        except (json.JSONDecodeError, OSError):
            pass
    return []


def _save_history(history: list[dict]) -> None:
    history = history[-365:]
    path = _history_path()
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as fh:
            json.dump(history, fh, indent=2)
    except OSError as exc:
        _log(f"Failed to save capacity history: {exc}")


def predict_days_to_full(free_space: dict) -> int | None:
    """
    Predict days until the pool is full, based on historical usage rate.

    Returns None if insufficient data (fewer than 7 points).
    """
    history = _load_history()
    if len(history) < 7:
        return None

    recent = history[-30:]
    first = recent[0]
    last = recent[-1]

    try:
        first_date = datetime.fromisoformat(first["timestamp"])
        last_date = datetime.fromisoformat(last["timestamp"])
        days_elapsed = (last_date - first_date).total_seconds() / 86400.0

        if days_elapsed < 1.0:
            return None

        usage_growth = last["total_used_gib"] - first["total_used_gib"]
        daily_rate = usage_growth / days_elapsed

        if daily_rate <= 0:
            return None

        remaining_gib = free_space["real_free_gib"]
        return max(0, int(remaining_gib / daily_rate))
    except (KeyError, ValueError, TypeError):
        return None


def record_snapshot(free_space: dict) -> None:
    """Append current capacity data to the history file."""
    history = _load_history()
    entry = {
        "timestamp": datetime.now().isoformat(),
        "total_used_gib": free_space.get("total_used_gib", 0),
        "real_free_gib": free_space.get("real_free_gib", 0),
        "usable_ceiling_gib": free_space.get("usable_ceiling_gib", 0),
        "pct_used": free_space.get("pct_used", 0),
    }
    history.append(entry)
    _save_history(history)


# ── Public interface ─────────────────────────────────────────────────

def run_capacity_report() -> None:
    """Run a full capacity analysis, print the report, and log warnings."""
    require_pool()
    cfg = config.get()
    mount = get_pool_mount()

    usage = parse_usage()
    if usage is None:
        _log("ERROR: Could not parse BTRFS usage data.")
        return

    free_space = calculate_real_free_space(usage)
    meta_warnings = check_metadata_concentration(usage)
    days_to_full = predict_days_to_full(free_space)

    record_snapshot(free_space)

    print(f"\nBTRFS RAID1 Capacity Report — {mount}")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 65)

    print(f"\n  Total Raw Capacity:   {free_space['total_raw_gib']:.1f} GiB")
    print(f"  Largest Drive:        {free_space['largest_device_gib']:.1f} GiB")
    print(f"  RAID1 Usable Ceiling: {free_space['usable_ceiling_gib']:.1f} GiB")
    print(f"  Data Used:            {free_space['data_used_gib']:.1f} GiB")
    print(f"  Metadata Used:        {free_space['metadata_used_gib']:.1f} GiB")
    print(f"  Real Free Space:      {free_space['real_free_gib']:.1f} GiB")
    print(f"  Utilisation:          {free_space['pct_used']:.1f}%")

    if days_to_full is not None:
        print(f"  Days to Full:         ~{days_to_full}")
    else:
        print("  Days to Full:         insufficient data (need 7+ daily snapshots)")

    print("\n  Chunk Allocation:")
    data_chunks = usage.get("data_chunks", {})
    meta_chunks = usage.get("metadata_chunks", {})
    if data_chunks:
        print(f"    Data:     {data_chunks.get('used_gib', 0):.1f} / {data_chunks.get('total_gib', 0):.1f} GiB ({data_chunks.get('used_pct', 0):.1f}%)")
    if meta_chunks:
        print(f"    Metadata: {meta_chunks.get('used_gib', 0):.1f} / {meta_chunks.get('total_gib', 0):.1f} GiB ({meta_chunks.get('used_pct', 0):.1f}%)")

    print("\n  Per-Device Allocation:")
    print(f"  {'Device':<12} {'Data':>10} {'Meta':>10} {'System':>10} {'Unalloc':>12} {'Total':>10}")
    print("  " + "-" * 63)
    for dev_path in sorted(usage.get("per_device", {}).keys()):
        d = usage["per_device"][dev_path]
        print(
            f"  {dev_path:<12} "
            f"{d['data_gib']:>9.1f}G "
            f"{d['metadata_gib']:>9.3f}G "
            f"{d['system_gib']:>9.3f}G "
            f"{d['unallocated_gib']:>11.1f}G "
            f"{d['total_gib']:>9.1f}G"
        )

    if meta_warnings:
        print("\n  WARNINGS:")
        for w in meta_warnings:
            print(f"    ! {w}")

    chunk_warn_pct = cfg["capacity"]["chunk_fullness_warn_percent"]
    free_warn_pct = cfg["capacity"]["free_space_warn_percent"]

    if data_chunks and data_chunks.get("used_pct", 0) > chunk_warn_pct:
        print(f"    ! Data chunks are {data_chunks['used_pct']:.1f}% full — new chunk allocation imminent.")

    if free_space["pct_used"] > (100 - free_warn_pct):
        print(f"    ! Free space is critically low: {free_space['real_free_gib']:.1f} GiB remaining.")

    print("=" * 65)

    # Notify on warnings
    alerts = list(meta_warnings)
    if free_space["pct_used"] > (100 - free_warn_pct):
        alerts.append(
            f"Free space critically low: {free_space['real_free_gib']:.1f} GiB "
            f"({free_space['pct_used']:.1f}% utilised)."
        )
    if days_to_full is not None and days_to_full < 30:
        alerts.append(f"Pool predicted full in ~{days_to_full} days at current growth rate.")

    if alerts:
        notifier.send(
            "Capacity Warning",
            "\n".join(f"- {a}" for a in alerts),
            color=0xE67E22,
        )
