#!/usr/bin/env bash
# ==============================================================================
# Cyber Evidence Box (CEB) - Unified Startup Script for Raspberry Pi & Linux
# ==============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
echo "[CEB] Project Directory: $SCRIPT_DIR"

# 1. Ensure required storage directories exist
mkdir -p "$SCRIPT_DIR/storage/vault"
mkdir -p "$SCRIPT_DIR/storage/evidence"
mkdir -p /media/usb 2>/dev/null || true

# 2. Check Python Virtual Environment
if [ ! -d "$SCRIPT_DIR/Backend/venv" ]; then
    echo "[CEB] Creating Python virtual environment..."
    python3 -m venv "$SCRIPT_DIR/Backend/venv"
    "$SCRIPT_DIR/Backend/venv/bin/pip" install --upgrade pip
    "$SCRIPT_DIR/Backend/venv/bin/pip" install -r "$SCRIPT_DIR/Backend/requirements.txt"
fi

# 3. Start Backend in background
echo "[CEB] Starting FastAPI Backend on 0.0.0.0:8000..."
cd "$SCRIPT_DIR/Backend"
"$SCRIPT_DIR/Backend/venv/bin/uvicorn" app.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# 4. Start Frontend
echo "[CEB] Starting Vite Frontend on 0.0.0.0:5173..."
cd "$SCRIPT_DIR/frontend"
npm run dev -- --host 0.0.0.0 --port 5173 &
FRONTEND_PID=$!

trap "echo '[CEB] Stopping services...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null" EXIT INT TERM

wait
