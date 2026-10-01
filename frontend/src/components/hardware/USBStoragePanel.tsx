import React, { useState } from "react";
import {
  HardDrive,
  FolderOpen,
  Download,
  CheckCircle2,
  Lock,
  Unlock,
  RefreshCw,
  PlusCircle,
  MinusCircle,
  ExternalLink,
} from "lucide-react";
import type { USBStorageDevice } from "../../types";
import {
  ejectStorageDevice,
  toggleMockStorageDevice,
} from "../../services/hardwareApi";

interface Props {
  devices: USBStorageDevice[];
  onRefresh: () => void;
  onOpenFileManager: (device: USBStorageDevice) => void;
  onOpenExportModal: (device: USBStorageDevice) => void;
}

export const USBStoragePanel: React.FC<Props> = ({
  devices,
  onRefresh,
  onOpenFileManager,
  onOpenExportModal,
}) => {
  const [ejectingDev, setEjectingDev] = useState<string | null>(null);
  const [ejectMessage, setEjectMessage] = useState<{ [device: string]: string }>({});
  const [isAddingMock, setIsAddingMock] = useState(false);

  const formatGB = (bytes: number): string => {
    if (!bytes || bytes <= 0) return "0 GB";
    const gb = bytes / (1000 * 1000 * 1000);
    return `${gb.toFixed(1)} GB`;
  };

  const calculatePercent = (used: number, total: number): number => {
    if (!total || total <= 0) return 0;
    return Math.min(100, Math.round((used / total) * 100));
  };

  const handleEject = async (device: USBStorageDevice) => {
    if (!window.confirm(`Are you sure you want to safely eject ${device.name} (${device.device})?`)) {
      return;
    }
    setEjectingDev(device.device);
    try {
      const res = await ejectStorageDevice(device.device);
      setEjectMessage((prev) => ({
        ...prev,
        [device.device]: res.message || "USB READY TO REMOVE",
      }));
      setTimeout(() => {
        onRefresh();
      }, 1000);
    } catch (err: any) {
      alert(`Eject failed: ${err.response?.data?.detail || err.message}`);
    } finally {
      setEjectingDev(null);
    }
  };

  const handleToggleMock = async () => {
    setIsAddingMock(true);
    try {
      // Toggle a secondary mock pendrive /dev/sdb1
      const hasMockSdb1 = devices.some((d) => d.device === "/dev/sdb1");
      if (hasMockSdb1) {
        await toggleMockStorageDevice("remove", "/dev/sdb1");
      } else {
        await toggleMockStorageDevice("add", "/dev/sdb1", "Kingston DataTraveler 3.0");
      }
      onRefresh();
    } catch (err: any) {
      alert(`Mock toggle error: ${err.response?.data?.detail || err.message}`);
    } finally {
      setIsAddingMock(false);
    }
  };

  return (
    <div className="panel storage-panel">
      <div className="panel-header">
        <div>
          <h4>USB STORAGE & PENDRIVE MANAGEMENT</h4>
          <p>Forensic Flash Drives, External USB SSDs, & Export Destinations</p>
        </div>
        <div className="flex-row items-center gap-2">
          <button
            className="panel-action"
            onClick={handleToggleMock}
            disabled={isAddingMock}
            title="Simulate USB Storage insertion/removal"
          >
            {devices.some((d) => d.device === "/dev/sdb1") ? (
              <>
                <MinusCircle size={15} /> Remove Mock USB
              </>
            ) : (
              <>
                <PlusCircle size={15} /> Insert Mock USB
              </>
            )}
          </button>
          <button className="panel-action" onClick={onRefresh} title="Rescan USB Disks">
            <RefreshCw size={15} /> Refresh Storage
          </button>
        </div>
      </div>

      <div className="storage-device-grid">
        {devices.length === 0 ? (
          <div className="empty-storage-state">
            <HardDrive size={40} style={{ opacity: 0.4, marginBottom: "12px" }} />
            <p>No USB storage devices or pendrives detected.</p>
            <small>Insert a FAT32, exFAT, or ext4 USB drive into any Raspberry Pi USB port.</small>
          </div>
        ) : (
          devices.map((dev) => {
            const isMounted = dev.mounted;
            const percent = calculatePercent(dev.usedBytes, dev.totalBytes);
            const isEjecting = ejectingDev === dev.device;
            const statusMsg = ejectMessage[dev.device];

            return (
              <div
                key={dev.device}
                className={`storage-card ${isMounted ? "storage-mounted" : "storage-unmounted"}`}
              >
                {/* CARD HEADER */}
                <div className="card-top">
                  <div className="device-avatar storage-avatar">
                    <HardDrive size={24} className="text-blue-400" />
                  </div>
                  <div className="device-titles">
                    <h5>{dev.name}</h5>
                    <span className="device-port-code">{dev.device}</span>
                  </div>
                  <div className="flex-row items-center gap-1">
                    <span className={`status-pill ${isMounted ? "connected" : "disconnected"}`}>
                      <span className="dot" />
                      {isMounted ? "MOUNTED" : "UNMOUNTED"}
                    </span>
                  </div>
                </div>

                {/* NOTIFICATION BANNER */}
                {statusMsg && (
                  <div className="safe-remove-banner">
                    <CheckCircle2 size={16} />
                    <strong>{statusMsg}</strong>
                  </div>
                )}

                {/* DEVICE METADATA */}
                <div className="storage-meta-box">
                  <div className="meta-line">
                    <span className="meta-lbl">Mount Point:</span>
                    <strong className="meta-val">{dev.mountPoint || "Not Mounted"}</strong>
                  </div>
                  <div className="meta-line">
                    <span className="meta-lbl">Filesystem:</span>
                    <strong className="meta-val">{dev.filesystem?.toUpperCase() || "UNKNOWN"}</strong>
                  </div>
                  <div className="meta-line">
                    <span className="meta-lbl">Access:</span>
                    <strong className="meta-val">
                      {dev.readOnly ? (
                        <span className="ro-badge">
                          <Lock size={12} /> Read-Only
                        </span>
                      ) : (
                        <span className="rw-badge">
                          <Unlock size={12} /> Read / Write Available
                        </span>
                      )}
                    </strong>
                  </div>
                </div>

                {/* STORAGE CAPACITY METER */}
                <div className="capacity-section">
                  <div className="capacity-labels">
                    <span>Storage Usage</span>
                    <strong>
                      {formatGB(dev.usedBytes)} used / {formatGB(dev.totalBytes)}
                    </strong>
                  </div>

                  <div className="capacity-meter-bar">
                    <div
                      className={`capacity-meter-fill ${percent > 85 ? "meter-critical" : ""}`}
                      style={{ width: `${percent}%` }}
                    />
                  </div>

                  <div className="capacity-sub-info">
                    <span>{percent}% allocated</span>
                    <strong className="free-space-text">Free: {formatGB(dev.freeBytes)}</strong>
                  </div>
                </div>

                {/* TOUCH-FRIENDLY BUTTONS */}
                <div className="storage-card-actions">
                  <button
                    className="btn-touch btn-primary"
                    onClick={() => onOpenFileManager(dev)}
                    disabled={!isMounted}
                  >
                    <FolderOpen size={18} />
                    OPEN
                  </button>

                  <button
                    className="btn-touch btn-secondary"
                    onClick={() => onOpenExportModal(dev)}
                    disabled={!isMounted || dev.readOnly}
                  >
                    <Download size={18} />
                    EXPORT
                  </button>

                  <button
                    className="btn-touch btn-danger"
                    onClick={() => handleEject(dev)}
                    disabled={!isMounted || isEjecting}
                  >
                    <ExternalLink size={18} />
                    {isEjecting ? "Ejecting..." : "EJECT"}
                  </button>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
