#!/usr/bin/env bash
# ==============================================================================
# Cyber Evidence Box (CEB) - Production One-Click Launcher for Raspberry Pi SSD
# ==============================================================================
set -Eeuo pipefail

# ==============================================================================
# CONFIGURATION SECTION (Populated from detected project structure)
# ==============================================================================
# Auto-detect script location and root project directory (supports SSD mount locations)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [ -d "$SCRIPT_DIR/frontend" ] && [ -d "$SCRIPT_DIR/Backend" ]; then
    PROJECT_DIR="$SCRIPT_DIR"
elif [ -d "$SCRIPT_DIR/../frontend" ] && [ -d "$SCRIPT_DIR/../Backend" ]; then
    PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
else
    PROJECT_DIR="$SCRIPT_DIR"
fi

FRONTEND_DIR="$PROJECT_DIR/frontend"
BACKEND_DIR="$PROJECT_DIR/Backend"
LOGS_DIR="$PROJECT_DIR/logs"

FRONTEND_COMMAND="npm run dev -- --host 0.0.0.0 --port 5173"
BACKEND_COMMAND="uvicorn app.main:app --host 0.0.0.0 --port 8000"

FRONTEND_PORT="5173"
BACKEND_PORT="8000"

BACKEND_PID_FILE="$LOGS_DIR/backend.pid"
FRONTEND_PID_FILE="$LOGS_DIR/frontend.pid"
BACKEND_LOG="$LOGS_DIR/backend.log"
FRONTEND_LOG="$LOGS_DIR/frontend.log"

# ==============================================================================
# 1. SSD MOUNT & PROJECT VERIFICATION SAFETY CHECK
# ==============================================================================
echo "=================================================="
echo "  CYBER EVIDENCE BOX (CEB) - SYSTEM INITIALIZATION"
echo "=================================================="
echo "[CEB] Checking project location and storage mount..."

# Verify project directory exists and contains key indicator files
if [ ! -d "$PROJECT_DIR" ] || [ ! -f "$BACKEND_DIR/app/main.py" ] || [ ! -f "$FRONTEND_DIR/package.json" ]; then
    echo ""
    echo "=================================================="
    echo "  ERROR: Project SSD is not mounted or path is invalid!"
    echo "=================================================="
    echo "Expected Project Directory: $PROJECT_DIR"
    echo ""
    echo "Current Block Devices (lsblk):"
    lsblk || true
    echo ""
    echo "Current Mounts (findmnt):"
    findmnt || true
    echo ""
    echo "Disk Space (df -h):"
    df -h || true
    echo ""
    echo "Please ensure your SSD is securely plugged in and mounted."
    echo "Press Enter to exit..."
    read -r || true
    exit 1
fi

# Ensure logs directory exists
mkdir -p "$LOGS_DIR"
mkdir -p "$PROJECT_DIR/storage/vault" "$PROJECT_DIR/storage/evidence" 2>/dev/null || true

# Limit log files size if they exceed 10MB
for logfile in "$BACKEND_LOG" "$FRONTEND_LOG"; do
    if [ -f "$logfile" ]; then
        LOG_SIZE=$(stat -c%s "$logfile" 2>/dev/null || stat -f%z "$logfile" 2>/dev/null || echo 0)
        if [ "$LOG_SIZE" -gt 10485760 ]; then
            tail -n 2000 "$logfile" > "${logfile}.tmp" && mv "${logfile}.tmp" "$logfile"
        fi
    fi
done

echo "[CEB] Project Directory: $PROJECT_DIR"
echo "[CEB] Verified Backend:  $BACKEND_DIR"
echo "[CEB] Verified Frontend: $FRONTEND_DIR"

# ==============================================================================
# 2. DEPENDENCY & ENVIRONMENT CHECKS
# ==============================================================================
echo "[CEB] Verifying runtime dependencies..."

# Python check
if ! command -v python3 >/dev/null 2>&1; then
    echo "ERROR: python3 is not installed on this system. Please run: sudo apt install -y python3 python3-venv"
    exit 1
fi

# Node & npm check
if ! command -v node >/dev/null 2>&1 || ! command -v npm >/dev/null 2>&1; then
    echo "ERROR: Node.js and npm are required for CEB Frontend. Please install Node.js (v18+)."
    exit 1
fi

# Python virtual environment check
VENV_DIR="$BACKEND_DIR/venv"
VENV_PYTHON="$VENV_DIR/bin/python"
VENV_UVICORN="$VENV_DIR/bin/uvicorn"

if [ ! -d "$VENV_DIR" ] || [ ! -x "$VENV_PYTHON" ]; then
    echo "[CEB] Virtual environment missing or incomplete. Initializing $VENV_DIR..."
    python3 -m venv "$VENV_DIR"
    "$VENV_DIR/bin/pip" install --upgrade pip
    if [ -f "$BACKEND_DIR/requirements.txt" ]; then
        "$VENV_DIR/bin/pip" install -r "$BACKEND_DIR/requirements.txt"
    fi
fi

# Node modules check
if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
    echo "[CEB] node_modules missing in frontend. Installing dependencies (npm install)..."
    (cd "$FRONTEND_DIR" && npm install)
fi

# ==============================================================================
# 3. HELPER FUNCTIONS FOR PROCESS MANAGEMENT
# ==============================================================================
is_port_in_use() {
    local port="$1"
    if command -v ss >/dev/null 2>&1; then
        ss -tuln | grep -q ":${port} " && return 0
    elif command -v lsof >/dev/null 2>&1; then
        lsof -i:"${port}" >/dev/null 2>&1 && return 0
    elif command -v netstat >/dev/null 2>&1; then
        netstat -tuln | grep -q ":${port} " && return 0
    fi
    return 1
}

is_pid_running() {
    local pid="$1"
    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
        return 0
    fi
    return 1
}

# ==============================================================================
# 4. PREVENT DUPLICATE PROCESSES
# ==============================================================================
BACKEND_RUNNING=0
FRONTEND_RUNNING=0

if [ -f "$BACKEND_PID_FILE" ]; then
    OLD_BACKEND_PID=$(cat "$BACKEND_PID_FILE" 2>/dev/null || echo "")
    if is_pid_running "$OLD_BACKEND_PID"; then
        BACKEND_RUNNING=1
    fi
fi

if is_port_in_use "$BACKEND_PORT"; then
    BACKEND_RUNNING=1
fi

if [ -f "$FRONTEND_PID_FILE" ]; then
    OLD_FRONTEND_PID=$(cat "$FRONTEND_PID_FILE" 2>/dev/null || echo "")
    if is_pid_running "$OLD_FRONTEND_PID"; then
        FRONTEND_RUNNING=1
    fi
fi

if is_port_in_use "$FRONTEND_PORT"; then
    FRONTEND_RUNNING=1
fi

# ==============================================================================
# 5. DETECT GRAPHICAL TERMINAL EMULATORS
# ==============================================================================
HAS_GUI=0
TERMINAL_EMU=""

if [ -n "${DISPLAY:-}" ] || [ -n "${WAYLAND_DISPLAY:-}" ]; then
    HAS_GUI=1
    for term in lxterminal x-terminal-emulator gnome-terminal xfce4-terminal mate-terminal konsole alacritty kitty foot xterm; do
        if command -v "$term" >/dev/null 2>&1; then
            TERMINAL_EMU="$term"
            break
        fi
    done
fi

# ==============================================================================
# 6. START BACKEND
# ==============================================================================
if [ "$BACKEND_RUNNING" -eq 1 ]; then
    echo "[CEB] Backend is already running on port $BACKEND_PORT."
else
    echo "[CEB] Launching Backend on 0.0.0.0:$BACKEND_PORT..."
    TIMESTAMP=$(date "+%Y-%m-%d %H:%M:%S")
    echo "--- CEB Backend Started at $TIMESTAMP ---" >> "$BACKEND_LOG"

    # Start Backend in dedicated terminal if GUI is present and requested, otherwise daemonize with logging
    if [ "$HAS_GUI" -eq 1 ] && [ -n "$TERMINAL_EMU" ] && [ "${CEB_TERMINAL_WINDOWS:-0}" = "1" ]; then
        case "$TERMINAL_EMU" in
            lxterminal)
                lxterminal --title="CEB BACKEND" --working-directory="$BACKEND_DIR" -e "bash -c 'echo [CEB BACKEND] Command: $VENV_UVICORN app.main:app --host 0.0.0.0 --port $BACKEND_PORT; $VENV_UVICORN app.main:app --host 0.0.0.0 --port $BACKEND_PORT 2>&1 | tee -a \"$BACKEND_LOG\"; exec bash'" &
                ;;
            gnome-terminal)
                gnome-terminal --title="CEB BACKEND" --working-directory="$BACKEND_DIR" -- bash -c "$VENV_UVICORN app.main:app --host 0.0.0.0 --port $BACKEND_PORT 2>&1 | tee -a '$BACKEND_LOG'; exec bash" &
                ;;
            xfce4-terminal)
                xfce4-terminal --title="CEB BACKEND" --working-directory="$BACKEND_DIR" -e "bash -c '$VENV_UVICORN app.main:app --host 0.0.0.0 --port $BACKEND_PORT 2>&1 | tee -a \"$BACKEND_LOG\"; exec bash'" &
                ;;
            *)
                x-terminal-emulator -T "CEB BACKEND" -e "bash -c '$VENV_UVICORN app.main:app --host 0.0.0.0 --port $BACKEND_PORT 2>&1 | tee -a \"$BACKEND_LOG\"; exec bash'" &
                ;;
        esac
    else
        (
            cd "$BACKEND_DIR"
            nohup "$VENV_UVICORN" app.main:app --host 0.0.0.0 --port "$BACKEND_PORT" >> "$BACKEND_LOG" 2>&1 &
            echo $! > "$BACKEND_PID_FILE"
        )
    fi
fi

# ==============================================================================
# 7. START FRONTEND
# ==============================================================================
if [ "$FRONTEND_RUNNING" -eq 1 ]; then
    echo "[CEB] Frontend is already running on port $FRONTEND_PORT."
else
    echo "[CEB] Launching Frontend on 0.0.0.0:$FRONTEND_PORT..."
    TIMESTAMP=$(date "+%Y-%m-%d %H:%M:%S")
    echo "--- CEB Frontend Started at $TIMESTAMP ---" >> "$FRONTEND_LOG"

    if [ "$HAS_GUI" -eq 1 ] && [ -n "$TERMINAL_EMU" ] && [ "${CEB_TERMINAL_WINDOWS:-0}" = "1" ]; then
        case "$TERMINAL_EMU" in
            lxterminal)
                lxterminal --title="CEB FRONTEND" --working-directory="$FRONTEND_DIR" -e "bash -c 'echo [CEB FRONTEND] Command: npm run dev -- --host 0.0.0.0 --port $FRONTEND_PORT; npm run dev -- --host 0.0.0.0 --port $FRONTEND_PORT 2>&1 | tee -a \"$FRONTEND_LOG\"; exec bash'" &
                ;;
            gnome-terminal)
                gnome-terminal --title="CEB FRONTEND" --working-directory="$FRONTEND_DIR" -- bash -c "npm run dev -- --host 0.0.0.0 --port $FRONTEND_PORT 2>&1 | tee -a '$FRONTEND_LOG'; exec bash" &
                ;;
            xfce4-terminal)
                xfce4-terminal --title="CEB FRONTEND" --working-directory="$FRONTEND_DIR" -e "bash -c 'npm run dev -- --host 0.0.0.0 --port $FRONTEND_PORT 2>&1 | tee -a \"$FRONTEND_LOG\"; exec bash'" &
                ;;
            *)
                x-terminal-emulator -T "CEB FRONTEND" -e "bash -c 'npm run dev -- --host 0.0.0.0 --port $FRONTEND_PORT 2>&1 | tee -a \"$FRONTEND_LOG\"; exec bash'" &
                ;;
        esac
    else
        (
            cd "$FRONTEND_DIR"
            nohup npm run dev -- --host 0.0.0.0 --port "$FRONTEND_PORT" >> "$FRONTEND_LOG" 2>&1 &
            echo $! > "$FRONTEND_PID_FILE"
        )
    fi
fi

# ==============================================================================
# 8. HEALTH CHECKS & VERIFICATION
# ==============================================================================
echo "[CEB] Verifying service startup..."

BACKEND_OK=0
for i in $(seq 1 15); do
    if is_port_in_use "$BACKEND_PORT" || (command -v curl >/dev/null 2>&1 && curl -sf "http://127.0.0.1:${BACKEND_PORT}/health" >/dev/null 2>&1); then
        BACKEND_OK=1
        break
    fi
    sleep 1
done

FRONTEND_OK=0
for i in $(seq 1 15); do
    if is_port_in_use "$FRONTEND_PORT"; then
        FRONTEND_OK=1
        break
    fi
    sleep 1
done

echo ""
if [ "$BACKEND_OK" -eq 1 ]; then
    echo "  ✓ Backend started successfully (Port $BACKEND_PORT)"
else
    echo "  ✗ Backend failed to start on port $BACKEND_PORT"
    echo "    Check logs at: $BACKEND_LOG"
fi

if [ "$FRONTEND_OK" -eq 1 ]; then
    echo "  ✓ Frontend started successfully (Port $FRONTEND_PORT)"
else
    echo "  ✗ Frontend failed to start on port $FRONTEND_PORT"
    echo "    Check logs at: $FRONTEND_LOG"
fi

# ==============================================================================
# 9. LAN IP & ACCESS DETAILS
# ==============================================================================
LAN_IP="127.0.0.1"
if command -v hostname >/dev/null 2>&1; then
    LAN_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "127.0.0.1")
fi
if [ -z "$LAN_IP" ] && command -v ip >/dev/null 2>&1; then
    LAN_IP=$(ip route get 1.1.1.1 2>/dev/null | awk '{print $7}' || echo "127.0.0.1")
fi

echo ""
echo "=================================================="
echo "  CEB SERVICES ARE RUNNING"
echo "=================================================="
echo "  Touchscreen / Frontend:"
echo "    Local:   http://localhost:$FRONTEND_PORT"
echo "    Network: http://${LAN_IP}:$FRONTEND_PORT"
echo ""
echo "  Forensic API / Backend:"
echo "    Local:   http://localhost:$BACKEND_PORT"
echo "    Network: http://${LAN_IP}:$BACKEND_PORT"
echo ""
echo "  Logs:"
echo "    $BACKEND_LOG"
echo "    $FRONTEND_LOG"
echo "=================================================="
echo "To stop all services, run: ./stop-ceb.sh"
echo "To restart services, run:  ./restart-ceb.sh"
echo "=================================================="
