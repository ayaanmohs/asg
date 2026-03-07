#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────
# ASG (Aldertech Storage Governor) — Installer
# ──────────────────────────────────────────────────────────────────────
# Installs the config file and sets up the command-line utility.
# Run as root: sudo bash setup.sh
# ──────────────────────────────────────────────────────────────────────

set -euo pipefail

CONFIG_DIR="/etc/asg"
STATE_DIR="/var/lib/asg"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "ASG (Aldertech Storage Governor) — Installer"
echo "============================================"

# Check root
if [ "$(id -u)" -ne 0 ]; then
    echo "ERROR: This script must be run as root."
    exit 1
fi

# Check btrfs-progs
if ! command -v btrfs &>/dev/null; then
    echo "ERROR: btrfs-progs is not installed."
    echo "Install it with: sudo apt install btrfs-progs"
    exit 1
fi

# Check Python
if ! command -v python3 &>/dev/null; then
    echo "ERROR: Python 3 is not installed."
    exit 1
fi

PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "Found Python ${PYTHON_VERSION}"

# Create config directory
mkdir -p "${CONFIG_DIR}"
mkdir -p "${STATE_DIR}"

# Install config (don't overwrite existing)
if [ -f "${CONFIG_DIR}/config.yaml" ]; then
    echo "Config already exists at ${CONFIG_DIR}/config.yaml — skipping."
    echo "New default config saved to ${CONFIG_DIR}/config.yaml.default"
    cp "${SCRIPT_DIR}/config.yaml" "${CONFIG_DIR}/config.yaml.default"
else
    cp "${SCRIPT_DIR}/config.yaml" "${CONFIG_DIR}/config.yaml"
    echo "Config installed to ${CONFIG_DIR}/config.yaml"
fi

# Install the package
echo "Installing asg..."
pip3 install "${SCRIPT_DIR}" --break-system-packages 2>/dev/null \
    || pip3 install "${SCRIPT_DIR}"

echo ""
echo "Installation complete."
echo ""
echo "Next steps:"
echo "  1. Edit your config:    sudo nano ${CONFIG_DIR}/config.yaml"
echo "  2. Set the mount point:  pool.mount should point to your BTRFS pool"
echo "  3. Test it:              asg status"
echo "  4. Test with dry-run:    asg scrub --dry-run"
echo ""
echo "Example crontab entries (add with: crontab -e):"
echo "  # Daily capacity report at 00:20"
echo "  20 0 * * * asg capacity >> ~/asg.log 2>&1"
echo "  # Weekly throttled scrub on Sunday at 02:00"
echo "  0 2 * * 0 asg scrub >> ~/asg.log 2>&1"
echo "  # Daily pre-backup snapshot at 02:00"
echo "  0 2 * * * asg snapshot >> ~/asg.log 2>&1"
