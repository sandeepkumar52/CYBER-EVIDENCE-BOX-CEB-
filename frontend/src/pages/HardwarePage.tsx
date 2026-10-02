import React, { useState, useEffect, useCallback } from "react";
import {
  HardDrive,
  Radio,
  RefreshCw,
  Layers,
  Activity,
  Usb,
  AlertTriangle,
} from "lucide-react";
import type {
  USBDevice,
  USBStorageDevice,
  HardwareSubsystemStatus,
  StorageSubsystemStatus,
} from "../types";
import {
  getUSBHardwareDevices,
  getHardwareSubsystemStatus,
  getUSBStorageDevices,
  getStorageSubsystemStatus,
} from "../services/hardwareApi";
import { hardwareWebSocket } from "../services/hardwareWebSocket";
import { USBHardwarePanel } from "../components/hardware/USBHardwarePanel";
import { USBStoragePanel } from "../components/hardware/USBStoragePanel";
import { FileManagerModal } from "../components/hardware/FileManagerModal";
import { USBExportModal } from "../components/hardware/USBExportModal";
import { ErrorBoundary } from "../components/ErrorBoundary";

export const HardwarePage: React.FC = () => {
  const [hardwareDevices, setHardwareDevices] = useState<USBDevice[]>([]);
  const [storageDevices, setStorageDevices] = useState<USBStorageDevice[]>([]);
  const [hwStatus, setHwStatus] = useState<HardwareSubsystemStatus | null>(null);
  const [storageStatus, setStorageStatus] = useState<StorageSubsystemStatus | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [notification, setNotification] = useState<string | null>(null);

  // Modals state
  const [fileManagerDevice, setFileManagerDevice] = useState<USBStorageDevice | null>(null);
  const [exportDevice, setExportDevice] = useState<USBStorageDevice | null>(null);

  const fetchAllHardwareData = useCallback(async () => {
    setLoading(true);
    setFetchError(null);
    try {
      const [hwDevs, hwStat, storDevs, storStat] = await Promise.all([
        getUSBHardwareDevices().catch((err) => {
          console.error("[HardwarePage] hwDevs error:", err);
          return [];
        }),
        getHardwareSubsystemStatus().catch((err) => {
          console.error("[HardwarePage] hwStat error:", err);
          return null;
        }),
        getUSBStorageDevices().catch((err) => {
          console.error("[HardwarePage] storDevs error:", err);
          return [];
        }),
        getStorageSubsystemStatus().catch((err) => {
          console.error("[HardwarePage] storStat error:", err);
          return null;
        }),
      ]);

      setHardwareDevices(Array.isArray(hwDevs) ? hwDevs : []);
      setHwStatus(hwStat);
      setStorageDevices(Array.isArray(storDevs) ? storDevs : []);
      setStorageStatus(storStat);
    } catch (err: any) {
      console.error("[HardwarePage] Failed to load hardware status:", err);
      setFetchError(err.message || "Failed to communicate with hardware subsystem.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAllHardwareData();

    // Setup WebSocket event subscriptions
    const unsubs = [
      hardwareWebSocket.on("storage:connected", (data) => {
        setNotification(`USB Storage Inserted: ${data?.device?.name || data?.device || "New Drive"}`);
        fetchAllHardwareData();
      }),
      hardwareWebSocket.on("storage:mounted", (data) => {
        setNotification(`USB Storage Mounted at ${data?.mountPoint || "target"}`);
        fetchAllHardwareData();
      }),
      hardwareWebSocket.on("storage:unmounted", () => {
        setNotification("USB Storage unmounted safely.");
        fetchAllHardwareData();
      }),
      hardwareWebSocket.on("storage:removed", (data) => {
        setNotification(`USB Storage Removed: ${data?.device || ""}`);
        fetchAllHardwareData();
      }),
      hardwareWebSocket.on("storage:ejected", () => {
        setNotification("USB READY TO REMOVE");
        fetchAllHardwareData();
      }),
      hardwareWebSocket.on("usb:connected", (data) => {
        setNotification(`USB Hardware Device Attached: ${data?.name || data?.port || ""}`);
        fetchAllHardwareData();
      }),
      hardwareWebSocket.on("usb:disconnected", (data) => {
        setNotification(`USB Hardware Device Detached: ${data?.port || ""}`);
        fetchAllHardwareData();
      }),
    ];

    // Periodic polling fallback every 8 seconds
    const interval = setInterval(fetchAllHardwareData, 8000);

    return () => {
      unsubs.forEach((unsub) => unsub());
      clearInterval(interval);
    };
  }, [fetchAllHardwareData]);

  // Auto-dismiss notification after 4 seconds
  useEffect(() => {
    if (notification) {
      const timer = setTimeout(() => setNotification(null), 4000);
      return () => clearTimeout(timer);
    }
  }, [notification]);

  const formatGB = (bytes?: number): string => {
    if (!bytes || bytes <= 0 || isNaN(bytes)) return "0 GB";
    const gb = bytes / (1000 * 1000 * 1000);
    return `${gb.toFixed(1)} GB`;
  };

  return (
    <ErrorBoundary fallbackTitle="Error loading Hardware & USB Storage Management">
      <div className="hardware-page-shell">
        {/* HEADER SECTION */}
        <div className="welcome-row">
          <div>
            <p className="eyebrow">RASPBERRY PI 4 / EMBEDDED INTEGRATION</p>
            <h3>CEB HARDWARE & STORAGE STATUS</h3>
            <p className="muted">
              Live telemetry, microcontrollers (ESP32/GPS/Sensors), USB pendrives, block storage, and export management.
            </p>
          </div>

          <button className="primary-button" onClick={fetchAllHardwareData} disabled={loading}>
            <RefreshCw size={18} className={loading ? "animate-spin" : ""} />
            Scan All USB Busses
          </button>
        </div>

        {/* REAL-TIME NOTIFICATION TOAST */}
        {notification && (
          <div className="hardware-notification-toast">
            <Usb size={18} />
            <span>{notification}</span>
          </div>
        )}

        {/* ERROR STATE BANNER */}
        {fetchError && (
          <div className="fm-error-banner" style={{ marginBottom: "20px" }}>
            <AlertTriangle size={18} />
            <span>{fetchError} — check backend connection.</span>
            <button
              onClick={fetchAllHardwareData}
              style={{
                marginLeft: "auto",
                background: "transparent",
                border: "1px solid currentColor",
                color: "inherit",
                padding: "4px 10px",
                borderRadius: "4px",
                cursor: "pointer"
              }}
            >
              Retry
            </button>
          </div>
        )}

        {/* SUMMARY KPI CARDS */}
        <section className="stats-grid">
          <div className="stat-card">
            <div className="stat-icon">
              <Radio size={21} />
            </div>
            <div className="stat-content">
              <span>USB Hardware Devices</span>
              <strong>{hardwareDevices.length}</strong>
              <small>
                {hwStatus
                  ? `${hwStatus.connectedCount ?? 0} of ${hwStatus.totalDevices ?? hardwareDevices.length} connected`
                  : loading
                  ? "Scanning..."
                  : "0 connected"}
              </small>
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-icon">
              <HardDrive size={21} />
            </div>
            <div className="stat-content">
              <span>USB Storage / Pendrives</span>
              <strong>{storageDevices.length}</strong>
              <small>
                {storageStatus
                  ? `${storageStatus.mountedCount ?? 0} of ${storageStatus.totalStorageDevices ?? storageDevices.length} mounted`
                  : loading
                  ? "Scanning..."
                  : "0 mounted"}
              </small>
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-icon">
              <Layers size={21} />
            </div>
            <div className="stat-content">
              <span>Available USB Space</span>
              <strong>{storageStatus ? formatGB(storageStatus.freeBytes) : "-"}</strong>
              <small>
                {storageStatus?.totalBytes && storageStatus.totalBytes > 0
                  ? `Total: ${formatGB(storageStatus.totalBytes)}`
                  : "No drive mounted"}
              </small>
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-icon">
              <Activity size={21} />
            </div>
            <div className="stat-content">
              <span>Hardware Mode</span>
              <strong>{(hwStatus?.mode || "AUTO").toUpperCase()}</strong>
              <small>Raspberry Pi Hardware Subsystem</small>
            </div>
          </div>
        </section>

        {/* SECTION 1: USB HARDWARE (ESP32, GPS, SENSORS, ARDUINO) */}
        <ErrorBoundary fallbackTitle="Error loading USB Serial & Hardware Controllers">
          <USBHardwarePanel
            devices={hardwareDevices}
            onRefresh={fetchAllHardwareData}
          />
        </ErrorBoundary>

        {/* SECTION 2: USB STORAGE (PENDRIVES, FLASH DRIVES, EXTERNAL DISKS) */}
        <ErrorBoundary fallbackTitle="Error loading USB Storage & Pendrive Panel">
          <USBStoragePanel
            devices={storageDevices}
            onRefresh={fetchAllHardwareData}
            onOpenFileManager={(device) => setFileManagerDevice(device)}
            onOpenExportModal={(device) => setExportDevice(device)}
          />
        </ErrorBoundary>

        {/* MODAL: TOUCHSCREEN FILE MANAGER */}
        {fileManagerDevice && (
          <ErrorBoundary fallbackTitle="Error in File Explorer">
            <FileManagerModal
              device={fileManagerDevice}
              isOpen={!!fileManagerDevice}
              onClose={() => setFileManagerDevice(null)}
              onOpenExportModal={(device) => setExportDevice(device)}
              onEjected={fetchAllHardwareData}
            />
          </ErrorBoundary>
        )}

        {/* MODAL: CEB DATA EXPORT TO USB */}
        {exportDevice && (
          <ErrorBoundary fallbackTitle="Error in USB Export Modal">
            <USBExportModal
              device={exportDevice}
              isOpen={!!exportDevice}
              onClose={() => setExportDevice(null)}
              onExportSuccess={fetchAllHardwareData}
            />
          </ErrorBoundary>
        )}
      </div>
    </ErrorBoundary>
  );
};

