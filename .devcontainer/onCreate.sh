#!/usr/bin/env bash
set -euo pipefail

# This script runs as root during the container creation phase.
# It installs all necessary system packages.

echo "--- Running apt-get update ---"
apt-get update -y

echo "--- Installing system packages ---"
apt-get install -y --no-install-recommends \
    python3-venv \
    python3-pip \
    python3-dev \
    build-essential \
    git \
    curl \
    ca-certificates

echo "--- Cleaning up apt cache ---"
rm -rf /var/lib/apt/lists/*

# Ensure python3 is available
if ! command -v python3 >/dev/null 2>&1; then
    echo "ERROR: python3 not available"
    exit 1
fi

# Speed up pip globally (will be inherited by the vscode user)
echo "--- Configuring pip ---"
python3 -m pip config set global.progress_bar off || true

echo "--- onCreate.sh completed successfully ---"