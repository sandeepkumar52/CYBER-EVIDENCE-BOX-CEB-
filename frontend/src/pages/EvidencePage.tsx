import React, { useEffect, useState } from "react";
import {
  Archive,
  CheckCircle,
  CircleAlert,
  Hash,
  PackageSearch,
  Plus,
  Search,
  ShieldCheck,
  Upload,
  Lock,
} from "lucide-react";
import api from "../services/api";
import type { Case, Evidence, EvidenceVerifyResult } from "../types";
import { EvidenceViewerModal } from "../components/EvidenceViewerModal";

interface Props {
  cases: Case[];
  onOpenRegisterModal: () => void;
  onOpenUploadModal: (ev: Evidence) => void;
  onOpenCustodyModal: (ev: Evidence) => void;
}

export const EvidencePage: React.FC<Props> = ({
  onOpenRegisterModal,
  onOpenUploadModal,
  onOpenCustodyModal,
}) => {
  const [evidenceList, setEvidenceList] = useState<Evidence[]>([]);
  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState("All");
  const [statusFilter, setStatusFilter] = useState("All");
  const [loading, setLoading] = useState(true);
  const [verifyingId, setVerifyingId] = useState<string | null>(null);
  const [verifyResult, setVerifyResult] = useState<EvidenceVerifyResult | null>(null);
  const [viewEvidence, setViewEvidence] = useState<Evidence | null>(null);

  const fetchEvidence = async () => {
    try {
      setLoading(true);
      let url = "/evidence?limit=100";
      if (search) url += `&search=${encodeURIComponent(search)}`;
      if (typeFilter !== "All") url += `&evidence_type=${encodeURIComponent(typeFilter)}`;
      if (statusFilter !== "All") url += `&status=${encodeURIComponent(statusFilter)}`;

      const response = await api.get<Evidence[]>(url);
      setEvidenceList(response.data);
    } catch (err) {
      console.error("Failed to fetch evidence list:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchEvidence();
  }, [search, typeFilter, statusFilter]);

  const handleVerify = async (evidenceId: string) => {
    setVerifyingId(evidenceId);
    setVerifyResult(null);
    try {
      const response = await api.post<EvidenceVerifyResult>(`/evidence/${evidenceId}/verify`);
      setVerifyResult(response.data);
      fetchEvidence();
    } catch (err: any) {
      alert("Verification failed: " + (err.response?.data?.detail || err.message));
    } finally {
      setVerifyingId(null);
    }
  };

  const formatBytes = (bytes: number) => {
    if (!bytes) return "-";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB", "GB", "TB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
  };

  return (
    <div style={{ padding: "30px", maxWidth: "1700px", margin: "auto" }}>
      <div className="welcome-row">
        <div>
          <p className="eyebrow">EVIDENCE MANAGEMENT</p>
          <h3>Digital Evidence Registry</h3>
          <p className="muted">Preserve evidence metadata, calculate SHA-256 hashes, and verify integrity.</p>
        </div>

        <button className="primary-button" onClick={onOpenRegisterModal}>
          <Plus size={18} />
          Register New Evidence
        </button>
      </div>

      {verifyResult && (
        <div
          className={verifyResult.is_valid ? "success-banner" : "error-banner"}
          style={{ marginBottom: "20px", display: "flex", alignItems: "center", gap: "10px" }}
        >
          {verifyResult.is_valid ? <CheckCircle size={20} /> : <CircleAlert size={20} />}
          <div>
            <strong>{verifyResult.message}</strong>
            {verifyResult.computed_hash && (
              <div style={{ fontFamily: "monospace", fontSize: "10px", marginTop: "4px" }}>
                Computed Hash ({verifyResult.evidence_id}): {verifyResult.computed_hash}
              </div>
            )}
          </div>
        </div>
      )}

      <div className="search-bar-container">
        <div className="search-input-wrapper">
          <Search size={16} />
          <input
            type="text"
            className="form-control"
            placeholder="Search by Evidence ID, description, or device serial..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>

        <select
          className="form-control"
          style={{ width: "180px" }}
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value)}
        >
          <option value="All">All Types</option>
          <option value="Disk Image">Disk Image</option>
          <option value="USB Device">USB Device</option>
          <option value="Memory Dump">Memory Dump</option>
          <option value="Log File">Log File</option>
          <option value="Document">Document</option>
          <option value="Mobile Device">Mobile Device</option>
          <option value="Network Capture">Network Capture</option>
          <option value="Other">Other</option>
        </select>

        <select
          className="form-control"
          style={{ width: "180px" }}
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
        >
          <option value="All">All Statuses</option>
          <option value="Registered">Registered</option>
          <option value="Acquired">Acquired</option>
          <option value="Verified">Verified</option>
          <option value="Secured">Secured</option>
          <option value="Transferred">Transferred</option>
          <option value="Archived">Archived</option>
        </select>
      </div>

      <div className="panel">
        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>Evidence ID</th>
                <th>Type</th>
                <th>Device Identifier</th>
                <th>File Size</th>
                <th>Hash Algorithm & Value</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={7} style={{ textAlign: "center", padding: "30px" }}>
                    Loading evidence directory...
                  </td>
                </tr>
              ) : evidenceList.length === 0 ? (
                <tr>
                  <td colSpan={7} style={{ textAlign: "center", padding: "30px" }}>
                    No evidence records matching query.
                  </td>
                </tr>
              ) : (
                evidenceList.map((item) => (
                  <tr key={item.id}>
                    <td>
                      <div className="evidence-name">
                        <div className="file-icon">
                          {item.is_encrypted ? <Lock size={16} color="#059669" /> : <Archive size={16} />}
                        </div>
                        <div>
                          <strong>{item.evidence_id}</strong>
                          <span>
                            {item.description || item.evidence_type}
                            {item.is_encrypted && " (🔒 Encrypted)"}
                          </span>
                        </div>
                      </div>
                    </td>
                    <td>{item.evidence_type}</td>
                    <td>{item.device_identifier || "-"}</td>
                    <td>{formatBytes(item.file_size_bytes || 0)}</td>
                    <td>
                      <div className="hash">
                        <Hash size={14} />
                        {item.hash_value ? (
                          <span title={item.hash_value}>
                            {item.hash_algorithm}: {item.hash_value.substring(0, 14)}...
                          </span>
                        ) : (
                          <span style={{ color: "#647387" }}>File not uploaded</span>
                        )}
                      </div>
                    </td>
                    <td>
                      <span className={`integrity ${item.status === "Verified" ? "verified" : "processing"}`}>
                        {item.status}
                      </span>
                    </td>
                    <td>
                      <div style={{ display: "flex", gap: "6px" }}>
                        <button
                          className="secondary-button"
                          title="Upload Binary File"
                          onClick={() => onOpenUploadModal(item)}
                        >
                          <Upload size={14} /> Upload
                        </button>
                        <button
                          className="secondary-button"
                          title="Log Custody Transfer"
                          onClick={() => onOpenCustodyModal(item)}
                        >
                          <PackageSearch size={14} /> Custody
                        </button>
                        <button
                          className="secondary-button"
                          title="View Evidence"
                          onClick={() => setViewEvidence(item)}
                        >
                          <Lock size={14} /> View
                        </button>
                        <button
                          className="primary-button"
                          style={{ padding: "4px 8px", fontSize: "10px" }}
                          disabled={verifyingId === item.evidence_id || !item.hash_value}
                          onClick={() => handleVerify(item.evidence_id)}
                        >
                          <ShieldCheck size={14} />
                          {verifyingId === item.evidence_id ? "Checking..." : "Verify"}
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {viewEvidence && (
        <EvidenceViewerModal
          evidence={viewEvidence}
          onClose={() => setViewEvidence(null)}
        />
      )}
    </div>
  );
};
