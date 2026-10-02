import React, { useEffect, useState } from "react";
import { Usb, X, Play } from "lucide-react";
import { USBScanResultsModal } from "./USBScanResultsModal";
import api from "../services/api";

interface UsbEvent {
  event: string;
  device_id: string;
  vendor?: string;
  model?: string;
  capacity?: number | string;
}

export const USBScanModal: React.FC = () => {
  const [usbEvent, setUsbEvent] = useState<UsbEvent | null>(null);
  const [isScanning, setIsScanning] = useState(false);
  const [scanResults, setScanResults] = useState<{ mountPoint: string; files: any[] } | null>(null);

  useEffect(() => {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const host = window.location.hostname || "127.0.0.1";
    const wsUrl = `${protocol}//${host}:8000/ws`;
    
    let ws: WebSocket | null = null;
    try {
      ws = new WebSocket(wsUrl);

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data && (data.event === "usb_connected" || data.event === "storage:connected")) {
            const devObj = data.device || data;
            setUsbEvent({
              event: data.event,
              device_id: devObj.device_id || devObj.device || devObj.devicePath || "/dev/sda1",
              vendor: devObj.vendor || devObj.manufacturer || "USB Storage",
              model: devObj.model || devObj.name || devObj.product || "Removable Drive",
              capacity: devObj.capacity || devObj.totalBytes || devObj.total_bytes || "Unknown",
            });
          } else if (data && (data.event === "usb_removed" || data.event === "storage:removed")) {
            setUsbEvent(null);
          }
        } catch (e) {
          console.error("[USBScanModal] Failed to parse websocket message:", e);
        }
      };

      ws.onerror = () => {
        // Silently handle WS fallback
      };
    } catch {
      // Ignored
    }

    return () => {
      if (ws) {
        try {
          ws.close();
        } catch {
          // Ignored
        }
      }
    };
  }, []);

  if (!usbEvent && !scanResults) return null;

  const handleStartScan = async () => {
    if (!usbEvent) return;
    setIsScanning(true);
    try {
      const response = await api.post("/hardware/usb/scan", { device_id: usbEvent.device_id });
      setScanResults({
        mountPoint: response.data?.mount_point || "",
        files: Array.isArray(response.data?.files) ? response.data.files : [],
      });
    } catch (e: any) {
      alert("Failed to scan USB: " + (e.response?.data?.detail || e.message));
    } finally {
      setIsScanning(false);
    }
  };

  const handleAcquire = async (file: any, caseId: number) => {
    if (!scanResults || !usbEvent) return;
    try {
      await api.post("/hardware/usb/acquire-file", {
        case_id: caseId,
        mount_point: scanResults.mountPoint,
        file_path: file.full_path,
        relative_path: file.relative_path,
        sha256: file.sha256,
        file_size: file.size,
        mime_type: file.mime_type,
      });
      alert(`Evidence securely encrypted into the vault!`);
    } catch (e: any) {
      alert("Failed to acquire evidence: " + (e.response?.data?.detail || e.message));
    }
  };

  const handleCloseResults = async () => {
    if (scanResults?.mountPoint) {
      try {
        await api.post(`/hardware/usb/unmount?mount_point=${encodeURIComponent(scanResults.mountPoint)}`);
      } catch (e) {
        console.error("Unmount failed", e);
      }
    }
    setScanResults(null);
    setUsbEvent(null);
  };

  if (scanResults && usbEvent) {
    return (
      <USBScanResultsModal 
        deviceInfo={usbEvent} 
        mountPoint={scanResults.mountPoint}
        files={scanResults.files || []}
        onClose={handleCloseResults}
        onAcquire={handleAcquire}
      />
    );
  }

  if (!usbEvent) {
    return null;
  }

  const formatCapacity = (bytes?: any) => {
    if (!bytes) return "Unknown Capacity";
    const num = typeof bytes === "number" ? bytes : parseFloat(String(bytes));
    if (isNaN(num) || num <= 0) return typeof bytes === "string" ? bytes : "Unknown Capacity";
    const gb = (num / (1000 * 1000 * 1000)).toFixed(1);
    return `${gb} GB`;
  };

  return (
    <div className="modal-backdrop" style={{ zIndex: 9999 }}>
      <div className="modal-content" style={{ maxWidth: "450px" }}>
        <div className="modal-header" style={{ borderBottom: "none", paddingBottom: "0" }}>
          <h2><Usb size={18} /> USB DEVICE DETECTED</h2>
          <button className="icon-button" onClick={() => setUsbEvent(null)}>
            <X size={18} />
          </button>
        </div>
        <div className="modal-body" style={{ textAlign: "center", paddingTop: "10px" }}>
          <div style={{ margin: "20px 0", color: "#3b82f6" }}>
            <Usb size={64} />
          </div>
          <h3 style={{ fontSize: "1.5rem", marginBottom: "5px" }}>
            {usbEvent.vendor || "USB Storage"} {usbEvent.model || "Device"}
          </h3>
          <p style={{ color: "#647387", fontSize: "1.1rem" }}>
            {formatCapacity(usbEvent.capacity)}
          </p>
          <p style={{ margin: "20px 0", fontWeight: "500" }}>
            Device detected successfully.
          </p>

          <div style={{ display: "flex", gap: "10px", justifyContent: "center", marginTop: "30px" }}>
            <button className="secondary-button" onClick={() => setUsbEvent(null)}>
              Cancel
            </button>
            <button className="primary-button" onClick={handleStartScan} disabled={isScanning}>
              <Play size={16} /> {isScanning ? "Scanning..." : "Start Evidence Scan"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

