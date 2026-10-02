import React, { useState, useEffect, useRef } from "react";
import {
  Cpu,
  Navigation,
  Radio,
  Terminal,
  RefreshCw,
  Power,
  Send,
  CheckCircle2,
  AlertCircle,
} from "lucide-react";
import type { USBDevice, SerialDataPacket } from "../../types";
import {
  connectUSBSerialDevice,
  disconnectUSBSerialDevice,
  writeUSBSerialData,
  readUSBSerialBuffer,
} from "../../services/hardwareApi";
import { hardwareWebSocket } from "../../services/hardwareWebSocket";

interface Props {
  devices: USBDevice[];
  onRefresh: () => void;
}

export const USBHardwarePanel: React.FC<Props> = ({ devices, onRefresh }) => {
  const [selectedPort, setSelectedPort] = useState<string | null>(null);
  const [consoleLogs, setConsoleLogs] = useState<{ [port: string]: string[] }>({});
  const [commandInput, setCommandInput] = useState<string>("");
  const [baudRate, setBaudRate] = useState<number>(115200);
  const [loadingPort, setLoadingPort] = useState<string | null>(null);
  const logEndRef = useRef<HTMLDivElement | null>(null);

  const deviceList = Array.isArray(devices) ? devices : [];

  // Listen for live serial data from WebSocket
  useEffect(() => {
    const unsub = hardwareWebSocket.on("usb:data", (packet: SerialDataPacket) => {
      const targetPort = packet?.port || packet?.devicePath;
      if (targetPort && packet?.data) {
        setConsoleLogs((prev) => {
          const existing = prev[targetPort] || [];
          return {
            ...prev,
            [targetPort]: [...existing.slice(-150), packet.data],
          };
        });
      }
    });

    return () => {
      unsub();
    };
  }, []);

  // Auto-scroll console log
  useEffect(() => {
    if (selectedPort && logEndRef.current) {
      logEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [consoleLogs, selectedPort]);

  const handleOpenConsole = async (port: string) => {
    if (!port) return;
    setSelectedPort(port);
    try {
      const history = await readUSBSerialBuffer(port, 40);
      if (history && Array.isArray(history.lines)) {
        setConsoleLogs((prev) => ({
          ...prev,
          [port]: history.lines,
        }));
      }
    } catch (err) {
      console.error(`[USB Console] Failed to read buffer for ${port}:`, err);
    }
  };

  const handleToggleConnect = async (device: USBDevice) => {
    const port = device.port || device.devicePath || "";
    if (!port) return;

    setLoadingPort(port);
    try {
      const isConnected = (device.status || "").toLowerCase() === "connected";
      if (isConnected) {
        await disconnectUSBSerialDevice(port);
      } else {
        await connectUSBSerialDevice(port, baudRate);
      }
      onRefresh();
    } catch (err: any) {
      alert(`Action failed: ${err.response?.data?.detail || err.message}`);
    } finally {
      setLoadingPort(null);
    }
  };

  const handleSendCommand = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedPort || !commandInput.trim()) return;

    try {
      await writeUSBSerialData(selectedPort, commandInput);
      setConsoleLogs((prev) => ({
        ...prev,
        [selectedPort]: [...(prev[selectedPort] || []), `> ${commandInput}`],
      }));
      setCommandInput("");
    } catch (err: any) {
      alert(`Failed to send command: ${err.response?.data?.detail || err.message}`);
    }
  };

  const getRoleIcon = (role?: string) => {
    const r = (role || "").toLowerCase();
    switch (r) {
      case "esp32":
        return <Cpu size={22} className="text-cyan-400" />;
      case "gps":
        return <Navigation size={22} className="text-amber-400" />;
      case "arduino":
        return <Radio size={22} className="text-emerald-400" />;
      default:
        return <Radio size={22} className="text-blue-400" />;
    }
  };

  return (
    <div className="panel hardware-panel">
      <div className="panel-header">
        <div>
          <h4>USB SERIAL & HARDWARE CONTROLLERS</h4>
          <p>Microcontrollers, GPS Modules, Sensors, & Telemetry Interfaces</p>
        </div>
        <button className="panel-action" onClick={onRefresh} title="Scan Ports">
          <RefreshCw size={15} /> Refresh Hardware
        </button>
      </div>

      <div className="hardware-device-grid">
        {deviceList.length === 0 ? (
          <div className="empty-hardware-state">
            <Radio size={40} style={{ opacity: 0.4, marginBottom: "12px" }} />
            <p>No USB serial hardware devices detected.</p>
            <small>Connect ESP32, GPS, or Arduino devices via USB to inspect.</small>
          </div>
        ) : (
          deviceList.map((device, idx) => {
            const port = device.port || device.devicePath || `USB_PORT_${idx}`;
            const name = device.name || device.product || device.description || "USB Device";
            const role = (device.role || device.matchedRole || "generic").toLowerCase();
            const status = (device.status || "disconnected").toLowerCase();
            const isConnected = status === "connected";
            const isSelected = selectedPort === port;
            const vid = device.vid || device.vendorId || "----";
            const pid = device.pid || device.productId || "----";
            const baud = device.baudRate || 115200;

            return (
              <div
                key={port}
                className={`hardware-card ${isConnected ? "device-online" : "device-offline"} ${
                  isSelected ? "device-selected" : ""
                }`}
              >
                <div className="card-top">
                  <div className="device-avatar">{getRoleIcon(role)}</div>
                  <div className="device-titles">
                    <h5>{name}</h5>
                    <span className="device-port-code">{port}</span>
                  </div>
                  <span className={`status-pill ${status}`}>
                    {isConnected ? (
                      <CheckCircle2 size={13} style={{ marginRight: "4px" }} />
                    ) : (
                      <AlertCircle size={13} style={{ marginRight: "4px" }} />
                    )}
                    {status.toUpperCase()}
                  </span>
                </div>

                <div className="device-specs">
                  <div className="spec-row">
                    <span>Role</span>
                    <strong>{role.toUpperCase()}</strong>
                  </div>
                  <div className="spec-row">
                    <span>VID / PID</span>
                    <strong>
                      {vid}:{pid}
                    </strong>
                  </div>
                  <div className="spec-row">
                    <span>Baud Rate</span>
                    <strong>{baud} bps</strong>
                  </div>
                  {device.isMock && (
                    <div className="spec-row">
                      <span>Source</span>
                      <span className="mock-badge">SIMULATED / MOCK</span>
                    </div>
                  )}
                </div>

                <div className="device-actions">
                  <button
                    className={`btn-touch ${isConnected ? "btn-danger" : "btn-primary"}`}
                    onClick={() => handleToggleConnect(device)}
                    disabled={loadingPort === port}
                  >
                    <Power size={16} />
                    {loadingPort === port
                      ? "Processing..."
                      : isConnected
                      ? "Disconnect"
                      : "Connect"}
                  </button>

                  <button
                    className="btn-touch btn-secondary"
                    onClick={() => handleOpenConsole(port)}
                  >
                    <Terminal size={16} />
                    Console
                  </button>
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* LIVE SERIAL TERMINAL DRAWER */}
      {selectedPort && (
        <div className="serial-console-modal">
          <div className="serial-console-header">
            <div className="flex-row items-center gap-2">
              <Terminal size={18} />
              <strong>Serial Terminal: {selectedPort}</strong>
              <span className="baud-badge">{baudRate} bps</span>
            </div>
            <div className="flex-row items-center gap-2">
              <select
                value={baudRate}
                onChange={(e) => setBaudRate(Number(e.target.value))}
                className="touch-select"
              >
                <option value={9600}>9600 bps</option>
                <option value={19200}>19200 bps</option>
                <option value={38400}>38400 bps</option>
                <option value={57600}>57600 bps</option>
                <option value={115200}>115200 bps</option>
              </select>
              <button
                className="btn-touch btn-small"
                onClick={() => setConsoleLogs((prev) => ({ ...prev, [selectedPort]: [] }))}
              >
                Clear
              </button>
              <button
                className="btn-touch btn-small btn-secondary"
                onClick={() => setSelectedPort(null)}
              >
                Close
              </button>
            </div>
          </div>

          <div className="serial-terminal-body">
            {(!consoleLogs[selectedPort] || consoleLogs[selectedPort].length === 0) && (
              <div className="terminal-empty">
                Listening for stream on {selectedPort}... (Telemetry or NMEA GPS packets will appear here)
              </div>
            )}
            {consoleLogs[selectedPort]?.map((line, idx) => (
              <div key={idx} className="terminal-line">
                <span className="line-prefix">&gt;</span>
                <code>{line}</code>
              </div>
            ))}
            <div ref={logEndRef} />
          </div>

          <form onSubmit={handleSendCommand} className="serial-terminal-input-bar">
            <input
              type="text"
              placeholder="Send ASCII command or packet (e.g. AT+INFO, PING)..."
              value={commandInput}
              onChange={(e) => setCommandInput(e.target.value)}
              className="terminal-text-input"
            />
            <button type="submit" className="btn-touch btn-primary">
              <Send size={16} /> Send
            </button>
          </form>
        </div>
      )}
    </div>
  );
};

