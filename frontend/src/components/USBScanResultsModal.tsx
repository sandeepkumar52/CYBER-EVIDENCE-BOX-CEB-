import React, { useState } from "react";
import { Folder, File, ShieldAlert, CheckCircle, Search, X, Lock } from "lucide-react";

interface UsbFile {
  name: string;
  relative_path: string;
  size: number;
  mime_type: string;
  extension: string;
  created_time: number;
  modified_time: number;
  sha256: string;
  malware_status: string;
  full_path: string;
}

interface Props {
  deviceInfo: any;
  mountPoint?: string;
  files: UsbFile[];
  onClose: () => void;
  onAcquire: (file: UsbFile, caseId: number) => void;
}

export const USBScanResultsModal: React.FC<Props> = ({ deviceInfo, files, onClose, onAcquire }) => {
  const [selectedFile, setSelectedFile] = useState<UsbFile | null>(null);
  const [caseId, setCaseId] = useState<string>("");
  
  const formatBytes = (bytes: number) => {
    if (!bytes) return "-";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB", "GB", "TB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
  };

  const handleAcquire = () => {
    if (!selectedFile) return;
    if (!caseId) {
      alert("Please enter a Case ID to assign this evidence to.");
      return;
    }
    // In a real implementation we would fetch available cases or have a dropdown
    // For now we just pass the ID we want to associate it with (assuming 1 for dev)
    onAcquire(selectedFile, parseInt(caseId) || 1);
  };

  return (
    <div className="modal-backdrop" style={{ zIndex: 9998 }}>
      <div className="modal-content" style={{ maxWidth: "900px", display: "flex", flexDirection: "column", height: "80vh" }}>
        <div className="modal-header">
          <h2><Search size={18} /> USB File Discovery: {deviceInfo.vendor}</h2>
          <button className="icon-button" onClick={onClose}><X size={18} /></button>
        </div>

        <div className="modal-body" style={{ display: "flex", flex: 1, overflow: "hidden", padding: 0 }}>
          {/* File Tree / List */}
          <div style={{ flex: 2, borderRight: "1px solid #e2e8f0", overflowY: "auto", padding: "15px" }}>
            <h4 style={{ marginBottom: "15px", color: "#647387" }}>Discovered Files ({files.length})</h4>
            <div style={{ display: "flex", flexDirection: "column", gap: "5px" }}>
              {files.map((file, idx) => {
                const isMalware = file.malware_status !== "Clean";
                return (
                  <div 
                    key={idx}
                    onClick={() => setSelectedFile(file)}
                    style={{ 
                      display: "flex", 
                      alignItems: "center", 
                      gap: "10px", 
                      padding: "8px", 
                      borderRadius: "6px",
                      cursor: "pointer",
                      background: selectedFile?.relative_path === file.relative_path ? "#eff6ff" : "transparent",
                      border: selectedFile?.relative_path === file.relative_path ? "1px solid #bfdbfe" : "1px solid transparent"
                    }}
                  >
                    <File size={16} color={isMalware ? "#ef4444" : "#647387"} />
                    <div style={{ flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                      <div style={{ fontSize: "14px", fontWeight: 500, color: isMalware ? "#ef4444" : "inherit" }}>
                        {file.relative_path}
                      </div>
                      <div style={{ fontSize: "11px", color: "#94a3b8" }}>
                        {formatBytes(file.size)} • {file.mime_type}
                      </div>
                    </div>
                    {isMalware && <span title="Malware Detected"><ShieldAlert size={14} color="#ef4444" /></span>}
                  </div>
                );
              })}
              {files.length === 0 && (
                <div style={{ textAlign: "center", padding: "40px", color: "#94a3b8" }}>
                  <Folder size={48} style={{ opacity: 0.5, marginBottom: "10px" }} />
                  <p>No files found on this partition.</p>
                </div>
              )}
            </div>
          </div>

          {/* Details & Action Panel */}
          <div style={{ flex: 1, padding: "20px", background: "#f8fafc", overflowY: "auto" }}>
            {selectedFile ? (
              <div>
                <h3 style={{ wordBreak: "break-all", marginBottom: "5px" }}>{selectedFile.name}</h3>
                
                <div style={{ marginTop: "20px" }}>
                  <p style={{ fontSize: "12px", color: "#647387", textTransform: "uppercase", fontWeight: "bold" }}>Malware Scan</p>
                  {selectedFile.malware_status === "Clean" ? (
                    <div style={{ display: "flex", alignItems: "center", gap: "6px", color: "#059669", marginTop: "4px" }}>
                      <CheckCircle size={16} /> Clean
                    </div>
                  ) : (
                    <div style={{ display: "flex", alignItems: "center", gap: "6px", color: "#dc2626", marginTop: "4px" }}>
                      <ShieldAlert size={16} /> {selectedFile.malware_status}
                    </div>
                  )}
                </div>

                <div style={{ marginTop: "20px" }}>
                  <p style={{ fontSize: "12px", color: "#647387", textTransform: "uppercase", fontWeight: "bold" }}>Original Hash (SHA-256)</p>
                  <div style={{ 
                    fontFamily: "monospace", 
                    fontSize: "11px", 
                    background: "#e2e8f0", 
                    padding: "8px", 
                    borderRadius: "4px",
                    marginTop: "4px",
                    wordBreak: "break-all"
                  }}>
                    {selectedFile.sha256}
                  </div>
                </div>

                <div style={{ marginTop: "20px" }}>
                  <p style={{ fontSize: "12px", color: "#647387", textTransform: "uppercase", fontWeight: "bold" }}>File Info</p>
                  <table style={{ width: "100%", fontSize: "13px", marginTop: "4px" }}>
                    <tbody>
                      <tr><td style={{ padding: "4px 0", color: "#647387" }}>Size</td><td>{formatBytes(selectedFile.size)}</td></tr>
                      <tr><td style={{ padding: "4px 0", color: "#647387" }}>Type</td><td>{selectedFile.mime_type}</td></tr>
                      <tr><td style={{ padding: "4px 0", color: "#647387" }}>Modified</td><td>{new Date(selectedFile.modified_time * 1000).toLocaleString()}</td></tr>
                    </tbody>
                  </table>
                </div>

                <hr style={{ margin: "30px 0", border: 0, borderTop: "1px solid #e2e8f0" }} />

                <div className="form-group">
                  <label>Assign to Case ID (Database ID)</label>
                  <input 
                    type="number" 
                    className="form-control" 
                    value={caseId} 
                    onChange={e => setCaseId(e.target.value)} 
                    placeholder="e.g. 1"
                  />
                </div>

                <button 
                  className="primary-button" 
                  style={{ width: "100%", marginTop: "10px", justifyContent: "center" }}
                  onClick={handleAcquire}
                >
                  <Lock size={16} /> Acquire & Encrypt to Vault
                </button>
                <p style={{ fontSize: "11px", color: "#647387", textAlign: "center", marginTop: "10px" }}>
                  This will securely encrypt the file into the vault. The source USB will not be modified.
                </p>
              </div>
            ) : (
              <div style={{ height: "100%", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", color: "#94a3b8" }}>
                <File size={48} style={{ opacity: 0.5, marginBottom: "10px" }} />
                <p>Select a file to view metadata<br/>and acquire evidence.</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
