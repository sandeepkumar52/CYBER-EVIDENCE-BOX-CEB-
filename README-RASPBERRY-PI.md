# Cyber Evidence Box (CEB) — Raspberry Pi & SSD Operations Guide

This guide details how to operate, manage, update, and automate the **Cyber Evidence Box (CEB)** on a Raspberry Pi running from an external or dedicated SSD.

---

## 1. Project Directory & SSD Auto-Detection

The CEB launcher automatically resolves its absolute path on the SSD regardless of where the SSD is mounted (e.g., `/media/pi/SSD/`, `/mnt/ceb/`, `/srv/ceb/`, or `/home/pi/`).

### Project Layout:
```text
<PROJECT_ROOT>/                   <- Root directory on SSD
├── start-ceb.sh                  <- One-click launcher (starts Frontend & Backend)
├── stop-ceb.sh                   <- Safe process stopper
├── restart-ceb.sh                <- Safe restart utility
├── update-ceb.sh                 <- Safe Git update manager
├── CEB Launcher.desktop          <- Double-clickable desktop shortcut
├── ceb-app.service               <- Systemd service unit template
├── README-RASPBERRY-PI.md        <- This operational manual
├── Backend/                      <- FastAPI backend (Python 3)
│   ├── app/
│   ├── venv/                     <- Python virtual environment
│   └── requirements.txt
├── frontend/                     <- React + Vite touchscreen UI
│   ├── src/
│   ├── node_modules/
│   └── package.json
├── logs/                         <- Process and runtime logs
│   ├── backend.log
│   └── frontend.log
└── storage/                      <- Evidence vault and exports
```

---

## 2. How to Start the Application

### Option A: Desktop Shortcut (Touchscreen / GUI)
1. Double-click the **Cyber Evidence Box** icon on the Raspberry Pi desktop.
2. If prompted, click **Execute in Terminal**.

### Option B: Terminal Command
Navigate to the project folder on the SSD and run:
```bash
./start-ceb.sh
```

**What happens:**
1. Checks that the SSD is mounted and project files are intact.
2. Checks that Python, Node.js, and npm are available.
3. Automatically sets up the Python virtual environment (`Backend/venv`) and node modules if missing.
4. Checks if the backend (port 8000) or frontend (port 5173) is already running (prevents duplicate instances).
5. Starts the FastAPI backend and Vite frontend.
6. Displays the local and LAN IP URLs:
   - **Frontend UI:** `http://localhost:5173` or `http://<RASPBERRY_PI_IP>:5173`
   - **Backend API:** `http://localhost:8000` or `http://<RASPBERRY_PI_IP>:8000`

---

## 3. How to Stop the Application

To safely shut down the backend and frontend without killing unrelated system processes:
```bash
./stop-ceb.sh
```
This gracefully signals the processes via their PID files, frees ports 8000 and 5173, and ensures no orphan processes remain.

---

## 4. How to Restart the Application

To perform a quick restart:
```bash
./restart-ceb.sh
```

---

## 5. How to Update from GitHub

When new forensic features or patches are pushed to GitHub:
```bash
./update-ceb.sh
```

**Safety Guarantees in `update-ceb.sh`:**
- Checks for local uncommitted files. If local changes exist, it **aborts safely** without overwriting your local configuration.
- Never runs `git reset --hard` or destructive commands.
- Pulls updates from the current Git branch.
- Inspects whether `requirements.txt` or `package.json` changed and updates dependencies only when needed.
- Restarts both services and displays the updated commit hash and author.

---

## 6. How to Inspect Logs

Runtime output and diagnostics are stored in the `logs/` directory:

```bash
# Monitor Backend Logs live:
tail -f logs/backend.log

# Monitor Frontend Logs live:
tail -f logs/frontend.log
```

*Note: Logs are automatically capped at 10 MB to prevent disk exhaustion on embedded media.*

---

## 7. Automatic Startup on Boot (Appliance Mode)

To have the Raspberry Pi boot directly into CEB after powering on:

### Step 1: Install the systemd service file
```bash
# Inspect your actual SSD mount path:
pwd

# Copy service file to system directory:
sudo cp ceb-app.service /etc/systemd/system/

# Open the service file and ensure WorkingDirectory matches your SSD path:
sudo nano /etc/systemd/system/ceb-app.service
```

### Step 2: Enable the service
```bash
sudo systemctl daemon-reload
sudo systemctl enable ceb-app.service
```

### Step 3: Start and test the service
```bash
sudo systemctl start ceb-app.service
sudo systemctl status ceb-app.service
```

---

## 8. How to Disable Automatic Startup

If you wish to return to manual startup:
```bash
sudo systemctl stop ceb-app.service
sudo systemctl disable ceb-app.service
sudo systemctl daemon-reload
```

---

## 9. Troubleshooting

### Problem: `ERROR: Project SSD is not mounted`
- **Cause:** The SSD was disconnected or failed to automount upon boot.
- **Diagnostics:**
  ```bash
  lsblk
  findmnt
  df -h
  ```
- **Resolution:** Verify USB cable connection. Check `/etc/fstab` if you configured persistent UUID mounts for your SSD.

### Problem: Frontend or Backend fails to start
1. Inspect the relevant log file:
   ```bash
   cat logs/backend.log
   cat logs/frontend.log
   ```
2. Verify port availability:
   ```bash
   ss -tuln | grep -E ':(5173|8000)'
   ```
3. Run `./stop-ceb.sh` and then `./start-ceb.sh` to clear any stale ports.

### Problem: USB Serial devices or Pendrives permission denied
Ensure user `pi` belongs to the `dialout` and `plugdev` groups:
```bash
sudo usermod -a -G dialout,plugdev $USER
sudo chmod 775 /media/usb 2>/dev/null || true
```
