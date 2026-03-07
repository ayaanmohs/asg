"""
Pool Validator — safety gate for all BTRFS operations.

Before any command that touches the filesystem, call `validate_pool()`
to confirm:
  1. The mount point exists and is an active mount.
  2. The mounted BTRFS filesystem UUID matches the expected UUID (if configured).

This prevents catastrophic misoperation if drives are re-ordered,
the enclosure is disconnected, or the mount point is shadowed.
"""

import subprocess
import os

from . import config


class PoolValidationError(Exception):
    """Raised when pool validation fails."""


def _is_mountpoint(path: str) -> bool:
    """Check whether *path* is an active mount point."""
    try:
        result = subprocess.run(
            ["mountpoint", "-q", path],
            timeout=5,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def _get_mounted_uuid(path: str) -> str | None:
    """
    Retrieve the BTRFS filesystem UUID for the volume mounted at *path*.

    Uses `btrfs filesystem show` and parses the uuid line.
    Returns None if the UUID cannot be determined.
    """
    try:
        result = subprocess.run(
            ["sudo", "btrfs", "filesystem", "show", path],
            capture_output=True, text=True,
            timeout=10,
        )
        if result.returncode != 0:
            return None

        for line in result.stdout.splitlines():
            line = line.strip()
            if "uuid:" in line:
                parts = line.split("uuid:")
                if len(parts) == 2:
                    return parts[1].strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None

    return None


def get_pool_mount() -> str:
    """Return the configured pool mount point."""
    return config.get()["pool"]["mount"]


def validate_pool(*, quiet: bool = False) -> bool:
    """
    Validate that the expected BTRFS pool is mounted and accessible.

    Parameters
    ----------
    quiet : bool
        If True, return False instead of raising on failure.

    Returns
    -------
    bool
        True if validation passes.

    Raises
    ------
    PoolValidationError
        If validation fails and *quiet* is False.
    """
    cfg = config.get()
    mount = cfg["pool"]["mount"]
    expected_uuid = cfg["pool"].get("uuid", "").strip()

    # 1. Check the mount point directory exists
    if not os.path.isdir(mount):
        msg = f"Mount point does not exist: {mount}"
        if quiet:
            return False
        raise PoolValidationError(msg)

    # 2. Check it is actively mounted
    if not _is_mountpoint(mount):
        msg = f"Path is not an active mount point: {mount}"
        if quiet:
            return False
        raise PoolValidationError(msg)

    # 3. Retrieve the UUID
    actual_uuid = _get_mounted_uuid(mount)
    if actual_uuid is None:
        msg = (
            f"Could not determine BTRFS UUID for {mount}. "
            "Is btrfs-progs installed and the filesystem healthy?"
        )
        if quiet:
            return False
        raise PoolValidationError(msg)

    # 4. Compare UUID (only if one is pinned in config)
    if expected_uuid and actual_uuid != expected_uuid:
        msg = (
            f"UUID mismatch on {mount}! "
            f"Expected {expected_uuid}, got {actual_uuid}. "
            "Aborting to prevent damage to an unknown filesystem."
        )
        if quiet:
            return False
        raise PoolValidationError(msg)

    return True


def require_pool():
    """
    Convenience wrapper: validate the pool or abort with a clear message.

    Intended for use at the top of every CLI sub-command.
    """
    validate_pool(quiet=False)
