#!/usr/bin/env bash
# ==============================================================================
# Cyber Evidence Box (CEB) - Safe Process Terminator
# ==============================================================================
set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -d "$SCRIPT_DIR/frontend" ] && [ -d "$SCRIPT_DIR/Backend" ]; then
    PROJECT_DIR="$SCRIPT_DIR"
elif [ -d "$SCRIPT_DIR/../frontend" ] && [ -d "$SCRIPT_DIR/../Backend" ]; then
    PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
else
    PROJECT_DIR="$SCRIPT_DIR"
fi

LOGS_DIR="$PROJECT_DIR/logs"
BACKEND_PID_FILE="$LOGS_DIR/backend.pid"
FRONTEND_PID_FILE="$LOGS_DIR/frontend.pid"

FRONTEND_PORT="5173"
BACKEND_PORT="8000"

echo "=================================================="
echo "  CYBER EVIDENCE BOX (CEB) - STOPPING SERVICES"
echo "=================================================="

kill_process_by_pid_file() {
    local pid_file="$1"
    local name="$2"

    if [ -f "$pid_file" ]; then
        local pid
        pid=$(cat "$pid_file" 2>/dev/null || echo "")
        if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
            echo "[CEB] Stopping $name (PID: $pid)..."
            kill -15 "$pid" 2>/dev/null || true
            for _ in $(seq 1 5); do
                if ! kill -0 "$pid" 2>/dev/null; then
                    break
                fi
                sleep 1
            done
            if kill -0 "$pid" 2>/dev/null; then
                echo "[CEB] Force stopping $name (PID: $pid)..."
                kill -9 "$pid" 2>/dev/null || true
            fi
            echo "  ✓ $name stopped"
        else
            echo "[CEB] $name PID $pid was not active."
        fi
        rm -f "$pid_file"
    fi
}

kill_project_port() {
    local port="$1"
    local name="$2"
    local pids=""

    if command -v lsof >/dev/null 2>&1; then
        pids=$(lsof -ti:"$port" 2>/dev/null || echo "")
    elif command -v fuser >/dev/null 2>&1; then
        pids=$(fuser "$port/tcp" 2>/dev/null || echo "")
    elif command -v ss >/dev/null 2>&1; then
        pids=$(ss -lptn "sport = :$port" 2>/dev/null | grep -o 'pid=[0-9]*' | cut -d= -f2 | sort -u || echo "")
    fi

    if [ -n "$pids" ]; then
        for p in $pids; do
            if kill -0 "$p" 2>/dev/null; then
                echo "[CEB] Freeing port $port used by $name (PID: $p)..."
                kill -15 "$p" 2>/dev/null || true
                sleep 1
                if kill -0 "$p" 2>/dev/null; then
                    kill -9 "$p" 2>/dev/null || true
                fi
            fi
        done
    fi
}

# Stop processes via PID files
kill_process_by_pid_file "$BACKEND_PID_FILE" "Backend"
kill_process_by_pid_file "$FRONTEND_PID_FILE" "Frontend"

# Ensure ports 8000 and 5173 are freed
kill_project_port "$BACKEND_PORT" "Backend Port"
kill_project_port "$FRONTEND_PORT" "Frontend Port"

echo ""
echo "=================================================="
echo "  ✓ ALL CEB SERVICES HAVE BEEN SAFELY STOPPED"
echo "=================================================="
