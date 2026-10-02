#!/usr/bin/env bash
# ==============================================================================
# Cyber Evidence Box (CEB) - Production One-Click Launcher for Raspberry Pi SSD
# ==============================================================================
set -Eeuo pipefail

# Auto-detect script location and root project directory (supports SSD mount locations)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -d "$SCRIPT_DIR/frontend" ] && [ -d "$SCRIPT_DIR/Backend" ]; then
    PROJECT_DIR="$SCRIPT_DIR"
elif [ -d "$SCRIPT_DIR/../frontend" ] && [ -d "$SCRIPT_DIR/../Backend" ]; then
    PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
else
    PROJECT_DIR="$SCRIPT_DIR"
fi

exec "$PROJECT_DIR/start-ceb.sh"
