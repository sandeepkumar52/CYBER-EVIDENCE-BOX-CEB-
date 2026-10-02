#!/usr/bin/env bash
# ==============================================================================
# Cyber Evidence Box (CEB) - Safe Restart Script
# ==============================================================================
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "[CEB] Restarting Cyber Evidence Box services..."
"$SCRIPT_DIR/stop-ceb.sh"

sleep 2

exec "$SCRIPT_DIR/start-ceb.sh"
