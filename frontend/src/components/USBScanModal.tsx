import React, { useEffect, useState } from "react";
import { Usb, X, Play } from "lucide-react";

interface UsbEvent {
  event: string;
  device_id: string;
  vendor: string;
  model: string;
  capacity: number;
}

import { USBScanResultsModal } from "./USBScanResultsModal";
import api from "../services/api";

export const USBScanModal: React.FC = () => {
  const [usbEvent, setUsbEvent] = useState<UsbEvent | null>(null);
  const [isScanning, setIsScanning] = useState(false);
  const [scanResults, setScanResults] = useState<{ mountPoint: string, files: any[] } | null>(null);

  useEffect(() => {
    // Determine ws protocol based on http/https
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    // If we're on localhost frontend (e.g. 5173), we assume backend is on 8000
    const backendHost = window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1" 
                        ? "127.0.0.1:8000" 
                        : window.location.host; // fallback if served from same origin
    
    const ws = new WebSocket(`${protocol}//${backendHost}/ws`);

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.event === "usb_connected") {
          setUsbEvent(data as UsbEvent);
        } else if (data.event === "usb_removed") {
          // Close modal if the device is removed
          setUsbEvent(null);
        }
      } catch (e) {
        console.error("Failed to parse websocket message", e);
      }
    };

    return () => {
      ws.close();
    };
  }, []);

  if (!usbEvent && !scanResults) return null;

  const handleStartScan = async () => {
    if (!usbEvent) return;
    setIsScanning(true);
    try {
      const response = await api.post("/hardware/usb/scan", { device_id: usbEvent.device_id });
      setScanResults({
        mountPoint: response.data.mount_point,
        files: response.data.files
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
        mime_type: file.mime_type
      });
      alert(`Evidence securely encrypted into the vault!`);
    } catch (e: any) {
      alert("Failed to acquire evidence: " + (e.response?.data?.detail || e.message));
    }
  };

  const handleCloseResults = async () => {
    if (scanResults) {
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
        files={scanResults.files}
        onClose={handleCloseResults}
        onAcquire={handleAcquire}
      />
    );
  }

  if (!usbEvent) {
    return null;
  }

  const formatCapacity = (bytes: number) => {
    if (!bytes) return "Unknown Capacity";
    if (typeof bytes === 'string') return bytes; // If backend sent string
    const gb = (bytes / (1000 * 1000 * 1000)).toFixed(1);
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
            {usbEvent.vendor} {usbEvent.model}
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
