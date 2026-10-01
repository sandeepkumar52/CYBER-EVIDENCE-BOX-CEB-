# Cyber Evidence Box (CEB)

CEB is a digital forensic evidence management, hardware acquisition, and chain-of-custody platform engineered for deployment on **Raspberry Pi 4 / Linux embedded systems with 7-inch touchscreen displays** as well as desktop development environments.

---

## System Architecture

```text
Raspberry Pi 4 (CEB Enclosure)
│
├── USB Hardware / Serial Devices
│   ├── ESP32 Controller (/dev/ttyUSB0)
│   ├── GPS / GNSS Receiver (/dev/ttyUSB1)
│   ├── Arduino / Microcontrollers (/dev/ttyACM0)
│   └── Environmental & Hardware Sensors
│
├── USB Storage / Pendrives
│   ├── Flash Drives & Pendrives (/dev/sda1, /dev/sdb1)
│   ├── External USB SSDs / HDDs
│   └── Automatic Mount (/media/usb/<NAME>)
│
├── CEB Backend Service (FastAPI + Python 3)
│   ├── Hardware Abstraction Layer & Device Registry
│   ├── Storage & Block Device Detection (psutil / sysfs)
│   ├── Sandboxed Path Traversal-Protected File Manager
│   ├── Forensic Exporter (/CEB_DATA/export_.../)
│   ├── WebSocket Real-Time Event Bus (/hardware/ws)
│   └── REST APIs (/api/hardware, /api/storage, /api/cases, /api/evidence)
│
└── CEB Frontend Touchscreen UI (React + Vite + TypeScript)
    ├── Touch-Optimized (Min 44px touch targets for 7-inch display)
    ├── Central Hardware & Storage Dashboard
    ├── Live Serial Console & Telemetry Stream
    ├── Touchscreen File Explorer
    └── One-Touch Forensic Data Exporter
```

---

## Features

### 1. Dual USB Subsystem Architecture
- **USB Hardware Devices**: Dedicated support for microcontrollers (ESP32, Arduino), GPS/GNSS modules, and sensor boards. Detects VID/PID against a configurable `device_registry.json`, handles auto-reconnect, baud rate configuration, ring buffer logging, and bidirectional command/data streams.
- **USB Storage & Pendrives**: Independent management of block devices and partitions. Provides live capacity monitoring (total, used, and free space), filesystem detection (FAT32, exFAT, NTFS, ext4), and read/write availability.

### 2. Touchscreen USB File Manager
- Designed specifically for 7-inch embedded touch displays with large, accessible buttons.
- Browse directory hierarchies, create folders, inspect file metadata, and delete files with confirmation prompts.
- **Strict Sandboxing**: Enforces strict path traversal defenses preventing directory escape (rejects `../`, `/etc`, `/root`, symlinks, or parent traversals).

### 3. Forensic Data Exporter
- Exports cases, cryptographic hashes, evidence manifests, custody history, and audit logs to the selected USB storage drive.
- Standardized directory layout: `/CEB_DATA/export_YYYY-MM-DD_HH-MM-SS/`.
- Provides an animated export progress bar and manifest summary.

### 4. Safe Eject Protocol
- Gracefully unmounts filesystems using `sync` and `umount` to flush buffers and prevent partition corruption.
- Displays unambiguous `USB READY TO REMOVE` visual indicators before physical removal.

### 5. Real-Time WebSocket Telemetry
- Pushes instant updates to the frontend for both hardware and storage lifecycles:
  - `usb:connected`, `usb:disconnected`, `usb:data`, `usb:status`, `usb:error`
  - `storage:connected`, `storage:mounted`, `storage:unmounted`, `storage:removed`, `storage:ejecting`, `storage:ejected`, `storage:spaceChanged`, `storage:error`

---

## Raspberry Pi & Linux Deployment Requirements

### Linux System Packages
Ensure standard USB and filesystem utilities are installed on Raspberry Pi OS (Debian/Bookworm):

```bash
sudo apt update
sudo apt install -y \
  python3-pip \
  python3-venv \
  exfat-fuse \
  exfat-utils \
  ntfs-3g \
  dosfstools \
  util-linux \
  udev
```

### User Permissions
To allow the CEB backend service to communicate with USB serial ports and mount USB drives without root escalation:

1. **Serial Port Access**:
   ```bash
   sudo usermod -a -G dialout $USER
   sudo usermod -a -G plugdev $USER
   ```

2. **Mount Directory Permissions**:
   ```bash
   sudo mkdir -p /media/usb
   sudo chown -R $USER:$USER /media/usb
   sudo chmod 775 /media/usb
   ```

3. **Udev Rules (Optional for Persistent Device Links)**:
   Add `/etc/udev/rules.d/99-ceb-usb.rules`:
   ```udev
   # Allow plugdev group to access USB serial devices
   KERNEL=="ttyUSB*", MODE="0666", GROUP="dialout"
   KERNEL=="ttyACM*", MODE="0666", GROUP="dialout"
   ```
   Reload udev rules:
   ```bash
   sudo udevadm control --reload-rules && sudo udevadm trigger
   ```

---

## Hardware Modes & Configuration

CEB supports three hardware modes via environment variables:

| Variable | Values | Description |
| :--- | :--- | :--- |
| `HARDWARE_MODE` | `auto` (Default) | Automatically detects physical devices; gracefully generates simulated devices (ESP32, GPS, 64GB Pendrive) if run on dev machines without hardware attached. |
| `HARDWARE_MODE` | `hardware` | Physical Raspberry Pi / Linux mode only. Interacts directly with `/dev/ttyUSB*`, `/dev/ttyACM*`, `/dev/sd*`. |
| `HARDWARE_MODE` | `mock` | Pure offline simulation mode for UI testing and frontend prototyping without requiring hardware or Linux. |
| `AUTO_EXPORT_TO_USB` | `false` (Default) | When set to `true`, exports approved case/evidence logs automatically upon pendrive insertion. |

---

## Setup & Running

### Backend Setup

```bash
cd Backend
python -m venv venv

# On Linux / Raspberry Pi:
source venv/bin/activate

# On Windows:
.\venv\Scripts\activate

pip install -r requirements.txt

# Run server with live reload:
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Setup

```bash
cd frontend
npm install

# Run Vite development server:
npm run dev -- --host 0.0.0.0

# Build optimized production bundle:
npm run build
```

---

## Default Investigator Credentials

* **Admin:** `admin` / `admin123`
* **Investigator:** `investigator01` / `investigator123`

---

## REST API Reference

### USB Hardware Endpoints
- `GET /api/hardware/usb` - List detected USB serial/microcontroller devices
- `GET /api/hardware/usb/status` - Subsystem connection health and device count
- `POST /api/hardware/usb/connect` - Open serial port connection (`{ "port": "/dev/ttyUSB0", "baudRate": 115200 }`)
- `POST /api/hardware/usb/disconnect` - Close serial port connection
- `POST /api/hardware/usb/write` - Send ASCII/binary command to device
- `GET /api/hardware/usb/read` - Read historical buffer logs from ring buffer
- `WS /hardware/ws` - Full-duplex WebSocket for serial telemetry and device events

### USB Storage & Pendrive Endpoints
- `GET /api/storage/devices` - List all connected and mounted USB storage devices
- `GET /api/storage/status` - Total/used/free capacity across all mounted storage
- `GET /api/storage/files` - List directory items (`?device=/dev/sda1&path=/`)
- `GET /api/storage/file` - Get file metadata (`?device=/dev/sda1&path=/file.txt`)
- `POST /api/storage/mkdir` - Create directory (`{ "device": "/dev/sda1", "path": "/", "dirName": "DATA" }`)
- `POST /api/storage/copy` - Copy file within USB mount
- `POST /api/storage/move` - Move/rename file within USB mount
- `DELETE /api/storage/file` - Delete file or folder (`?device=/dev/sda1&path=/file.txt`)
- `POST /api/storage/eject` - Safely unmount and flush buffers (`{ "device": "/dev/sda1" }`)
- `POST /api/storage/export` - Export CEB database to USB (`{ "device": "/dev/sda1", "includeCases": true, ... }`)
- `POST /api/storage/mock/toggle` - Simulate plugging/unplugging mock drives for UI testing

---

## Automated Testing

To run the automated test suite covering all 21 test cases (core APIs, hardware serial lifecycles, block storage detection, file manager operations, safe eject, and path traversal protection):

```bash
cd Backend
pytest
```
