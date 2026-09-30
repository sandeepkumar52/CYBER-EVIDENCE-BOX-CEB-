import React, { useState } from "react";
import { Lock, Unlock, X, ShieldAlert, FileText, Download } from "lucide-react";
import api from "../services/api";
import type { Evidence } from "../types";

interface Props {
  evidence: Evidence;
  onClose: () => void;
}

export const EvidenceViewerModal: React.FC<Props> = ({ evidence, onClose }) => {
  const [isUnlocked, setIsUnlocked] = useState(false);
  const [verifying, setVerifying] = useState(false);
  const [authError, setAuthError] = useState("");
  const [streamUrl, setStreamUrl] = useState<string | null>(null);

  const handleVerify = async () => {
    setVerifying(true);
    setAuthError("");
    try {
      await api.post(`/evidence/${evidence.evidence_id}/unlock`);
      setIsUnlocked(true);
      
      // Load the stream URL
      const response = await api.get(`/evidence/${evidence.evidence_id}/stream`, {
        responseType: "blob",
      });
      const url = URL.createObjectURL(response.data);
      setStreamUrl(url);
    } catch (err: any) {
      setAuthError(err.response?.data?.detail || "Authentication failed.");
    } finally {
      setVerifying(false);
    }
  };

  const handleLockAndClose = async () => {
    try {
      await api.post(`/evidence/${evidence.evidence_id}/lock`);
    } catch (e) {
      console.error("Lock error", e);
    }
    
    if (streamUrl) {
      URL.revokeObjectURL(streamUrl);
    }
    onClose();
  };

  const isExecutable = evidence.description?.toLowerCase().match(/\.(exe|dll|bat|cmd|ps1|vbs|scr|js)$/);

  return (
    <div className="modal-backdrop">
      <div className="modal-content" style={{ maxWidth: isUnlocked ? "800px" : "400px", transition: "max-width 0.3s" }}>
        <div className="modal-header">
          <h2>
            {isUnlocked ? <Unlock size={18} /> : <Lock size={18} />} 
            {isUnlocked ? "Evidence Viewer" : "Protected Evidence"}
          </h2>
          <button className="icon-button" onClick={handleLockAndClose}>
            <X size={18} />
          </button>
        </div>

        <div className="modal-body">
          {!isUnlocked ? (
            <div style={{ textAlign: "center", padding: "20px 0" }}>
              <h3 style={{ marginBottom: "10px" }}>Evidence: {evidence.evidence_id}</h3>
              <div style={{ margin: "20px 0", color: "#647387" }}>
                <Lock size={48} />
              </div>
              {evidence.is_encrypted ? (
                <p>🔒 <strong>Encrypted</strong></p>
              ) : (
                <p>Protected Access</p>
              )}
              <p style={{ marginTop: "10px" }}>Fingerprint authentication required</p>
              
              {authError && (
                <div className="error-banner" style={{ margin: "15px 0" }}>
                  {authError}
                </div>
              )}

              <div style={{ marginTop: "30px", display: "flex", gap: "10px", justifyContent: "center" }}>
                <button className="secondary-button" onClick={onClose} disabled={verifying}>
                  Cancel
                </button>
                <button className="primary-button" onClick={handleVerify} disabled={verifying}>
                  {verifying ? "Verifying..." : "Verify Fingerprint"}
                </button>
              </div>
            </div>
          ) : (
            <div>
              <div className="success-banner" style={{ marginBottom: "20px" }}>
                ✓ Identity Verified. Evidence access authorized. Opening protected evidence...
              </div>

              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "15px" }}>
                <h3>{evidence.description || "Evidence File"}</h3>
                <button className="secondary-button" onClick={handleLockAndClose}>
                  <Lock size={16} /> Lock Evidence
                </button>
              </div>

              <div style={{ background: "#f8fafc", padding: "15px", borderRadius: "8px", border: "1px solid #e2e8f0" }}>
                {isExecutable ? (
                  <div style={{ textAlign: "center", padding: "40px 20px" }}>
                    <ShieldAlert size={48} color="#dc2626" style={{ marginBottom: "15px" }} />
                    <h3 style={{ color: "#dc2626" }}>⚠ Potentially Executable File</h3>
                    <p style={{ marginTop: "10px", fontWeight: "bold" }}>{evidence.description}</p>
                    
                    <div style={{ marginTop: "20px", textAlign: "left", display: "inline-block", background: "#fff", padding: "15px", borderRadius: "6px", border: "1px solid #e2e8f0" }}>
                      <p><strong>SHA-256:</strong> {evidence.hash_value}</p>
                      <p><strong>Encrypted Hash:</strong> {evidence.encrypted_sha256}</p>
                      <p><strong>Size:</strong> {evidence.file_size_bytes} bytes</p>
                      <p><strong>Malware Scan:</strong> <span style={{ color: "#dc2626", fontWeight: "bold" }}>THREAT DETECTED</span> (Placeholder)</p>
                    </div>
                  </div>
                ) : (
                  <div style={{ minHeight: "400px", display: "flex", flexDirection: "column", gap: "10px" }}>
                    {streamUrl && (
                      <iframe 
                        src={streamUrl} 
                        style={{ width: "100%", height: "400px", border: "none", background: "#fff", borderRadius: "4px" }}
                        title="Evidence Viewer"
                      />
                    )}
                    <a href={streamUrl || "#"} download={evidence.description || "evidence.bin"} className="primary-button" style={{ alignSelf: "flex-start", textDecoration: "none" }}>
                      <Download size={16} /> Download Copy
                    </a>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
