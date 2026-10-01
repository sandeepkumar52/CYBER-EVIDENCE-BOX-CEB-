import React, { useState } from "react";
import {
  Download,
  CheckCircle2,
  FileCheck,
  FolderTree,
  AlertCircle,
  X,
} from "lucide-react";
import type { USBStorageDevice, StorageExportResult } from "../../types";
import { exportDataToUSBStorage } from "../../services/hardwareApi";

interface Props {
  device: USBStorageDevice | null;
  isOpen: boolean;
  onClose: () => void;
  onExportSuccess?: () => void;
}

export const USBExportModal: React.FC<Props> = ({
  device,
  isOpen,
  onClose,
  onExportSuccess,
}) => {
  const [includeCases, setIncludeCases] = useState(true);
  const [includeEvidence, setIncludeEvidence] = useState(true);
  const [includeCustody, setIncludeCustody] = useState(true);
  const [includeAuditLogs, setIncludeAuditLogs] = useState(true);

  const [isExporting, setIsExporting] = useState(false);
  const [exportProgress, setExportProgress] = useState(0);
  const [exportResult, setExportResult] = useState<StorageExportResult | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  if (!isOpen || !device) return null;

  const handleStartExport = async () => {
    setIsExporting(true);
    setExportProgress(15);
    setErrorMessage(null);
    setExportResult(null);

    const progressTimer = setInterval(() => {
      setExportProgress((p) => {
        if (p >= 85) {
          clearInterval(progressTimer);
          return 85;
        }
        return p + 18;
      });
    }, 250);

    try {
      const res = await exportDataToUSBStorage({
        device: device.device,
        includeCases,
        includeEvidence,
        includeCustody,
        includeAuditLogs,
      });

      clearInterval(progressTimer);
      setExportProgress(100);
      setExportResult(res);
      if (onExportSuccess) {
        onExportSuccess();
      }
    } catch (err: any) {
      clearInterval(progressTimer);
      setIsExporting(false);
      setErrorMessage(
        err.response?.data?.detail || "Export operation failed. Check drive permissions."
      );
    } finally {
      setIsExporting(false);
    }
  };

  const handleReset = () => {
    setExportResult(null);
    setExportProgress(0);
    setErrorMessage(null);
  };

  return (
    <div className="file-manager-overlay" onClick={onClose}>
      <div className="usb-export-dialog" onClick={(e) => e.stopPropagation()}>
        {/* HEADER */}
        <div className="modal-header">
          <div className="flex-row items-center gap-3">
            <div className="export-icon-badge">
              <Download size={22} />
            </div>
            <div>
              <h3>EXPORT CEB SYSTEM DATA TO USB</h3>
              <span>Destination: {device.name} ({device.device})</span>
            </div>
          </div>
          <button className="btn-close-touch" onClick={onClose}>
            <X size={22} />
          </button>
        </div>

        {/* BODY */}
        <div className="modal-body">
          {exportResult ? (
            /* SUCCESS STATE */
            <div className="export-success-state">
              <div className="success-icon-wrap">
                <CheckCircle2 size={48} className="text-emerald-400" />
              </div>
              <h4>Export Complete!</h4>
              <p>All requested CEB forensic logs, reports, and manifests have been exported.</p>

              <div className="export-location-box">
                <span className="location-label">SAVED DIRECTORY:</span>
                <code className="location-path">{exportResult.savedPath}</code>
              </div>

              <div className="exported-files-summary">
                <strong>Exported Manifest & Files ({exportResult.files.length}):</strong>
                <ul>
                  {exportResult.files.map((file, idx) => (
                    <li key={idx}>
                      <FileCheck size={14} /> {file}
                    </li>
                  ))}
                </ul>
              </div>

              <div className="flex-row justify-end gap-2" style={{ marginTop: "24px" }}>
                <button className="btn-touch btn-secondary" onClick={handleReset}>
                  Export Another Batch
                </button>
                <button className="btn-touch btn-primary" onClick={onClose}>
                  Done
                </button>
              </div>
            </div>
          ) : isExporting ? (
            /* EXPORTING IN PROGRESS */
            <div className="export-progress-state">
              <h4>Exporting CEB Forensic Data...</h4>
              <p>Flushing database records and generating JSON/CSV audit trails...</p>

              <div className="export-meter-bar">
                <div
                  className="export-meter-fill"
                  style={{ width: `${exportProgress}%` }}
                />
              </div>

              <div className="progress-label">
                <span>{exportProgress}% complete</span>
                <span>Writing to /CEB_DATA/...</span>
              </div>
            </div>
          ) : (
            /* CONFIGURATION / FORM STATE */
            <div>
              <p className="export-instructions">
                Select the CEB database modules and forensic archives to bundle and transfer directly onto the
                connected USB drive:
              </p>

              <div className="export-options-grid">
                <label className="export-option-card">
                  <input
                    type="checkbox"
                    checked={includeCases}
                    onChange={(e) => setIncludeCases(e.target.checked)}
                  />
                  <div className="option-text">
                    <strong>Active & Archived Cases</strong>
                    <span>Full case directory metadata, timestamps, and investigator assignments.</span>
                  </div>
                </label>

                <label className="export-option-card">
                  <input
                    type="checkbox"
                    checked={includeEvidence}
                    onChange={(e) => setIncludeEvidence(e.target.checked)}
                  />
                  <div className="option-text">
                    <strong>Evidence Manifests & SHA-256 Hashes</strong>
                    <span>Cryptographic hash records and evidence registry items in CSV/JSON.</span>
                  </div>
                </label>

                <label className="export-option-card">
                  <input
                    type="checkbox"
                    checked={includeCustody}
                    onChange={(e) => setIncludeCustody(e.target.checked)}
                  />
                  <div className="option-text">
                    <strong>Chain of Custody Logs</strong>
                    <span>Chronological transfer history and evidence custody audit trace.</span>
                  </div>
                </label>

                <label className="export-option-card">
                  <input
                    type="checkbox"
                    checked={includeAuditLogs}
                    onChange={(e) => setIncludeAuditLogs(e.target.checked)}
                  />
                  <div className="option-text">
                    <strong>System & Hardware Audit Logs</strong>
                    <span>USB device insertion events, serial commands, and security operations.</span>
                  </div>
                </label>
              </div>

              <div className="export-destination-summary">
                <FolderTree size={16} />
                <span>Target Directory structure:</span>
                <code>{device.mountPoint || "/media/usb"}/CEB_DATA/export_YYYY-MM-DD_HH-MM-SS/</code>
              </div>

              {errorMessage && (
                <div className="fm-error-banner" style={{ marginTop: "16px" }}>
                  <AlertCircle size={18} />
                  <span>{errorMessage}</span>
                </div>
              )}

              <div className="flex-row justify-end gap-2" style={{ marginTop: "24px" }}>
                <button type="button" className="btn-touch btn-secondary" onClick={onClose}>
                  Cancel
                </button>
                <button
                  type="button"
                  className="btn-touch btn-primary"
                  onClick={handleStartExport}
                  disabled={!includeCases && !includeEvidence && !includeCustody && !includeAuditLogs}
                >
                  <Download size={18} />
                  EXPORT CEB DATA TO USB
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
