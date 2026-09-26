import React, { useEffect, useState } from "react";
import {
  Archive,
  ArrowLeft,
  CheckCircle,
  CircleAlert,
  Hash,
  Plus,
  ShieldCheck,
  Upload,
} from "lucide-react";
import api from "../services/api";
import type { Case, Evidence, EvidenceVerifyResult } from "../types";

interface Props {
  caseCode: string;
  onNavigate: (page: string, param?: string) => void;
  onOpenRegisterEvidence: (caseId: number) => void;
  onOpenUploadModal: (ev: Evidence) => void;
}

export const CaseDetailsPage: React.FC<Props> = ({
  caseCode,
  onNavigate,
  onOpenRegisterEvidence,
  onOpenUploadModal,
}) => {
  const [caseData, setCaseData] = useState<Case | null>(null);
  const [evidenceList, setEvidenceList] = useState<Evidence[]>([]);
  const [activeTab, setActiveTab] = useState<"evidence" | "custody">("evidence");
  const [loading, setLoading] = useState(true);
  const [verifyingId, setVerifyingId] = useState<string | null>(null);
  const [verifyResult, setVerifyResult] = useState<EvidenceVerifyResult | null>(null);

  const loadCaseDetails = async () => {
    try {
      setLoading(true);
      const [caseRes, evidenceRes] = await Promise.all([
        api.get<Case>(`/cases/${caseCode}`),
        api.get<Evidence[]>(`/evidence?case_code=${caseCode}`),
      ]);
      setCaseData(caseRes.data);
      setEvidenceList(evidenceRes.data);
    } catch (err) {
      console.error("Failed to load case details:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadCaseDetails();
  }, [caseCode]);

  const handleVerifyHash = async (evidenceId: string) => {
    setVerifyingId(evidenceId);
    setVerifyResult(null);
    try {
      const response = await api.post<EvidenceVerifyResult>(`/evidence/${evidenceId}/verify`);
      setVerifyResult(response.data);
      loadCaseDetails();
    } catch (err: any) {
      alert("Verification failed: " + (err.response?.data?.detail || err.message));
    } finally {
      setVerifyingId(null);
    }
  };

  if (loading) {
    return (
      <div style={{ padding: "40px", textAlign: "center", color: "#647387" }}>
        Loading case details for {caseCode}...
      </div>
    );
  }

  if (!caseData) {
    return (
      <div style={{ padding: "40px", textAlign: "center", color: "#ff6b6b" }}>
        Case {caseCode} not found.
      </div>
    );
  }

  return (
    <div style={{ padding: "30px", maxWidth: "1700px", margin: "auto" }}>
      <button
        className="secondary-button"
        style={{ display: "inline-flex", alignItems: "center", gap: "6px", marginBottom: "20px" }}
        onClick={() => onNavigate("cases")}
      >
        <ArrowLeft size={16} /> Back to Cases
      </button>

      <div className="welcome-row">
        <div>
          <p className="eyebrow">{caseData.case_id}</p>
          <h3>{caseData.case_name}</h3>
          <p className="muted">{caseData.description || "No description provided."}</p>
        </div>

        <button className="primary-button" onClick={() => onOpenRegisterEvidence(caseData.id)}>
          <Plus size={18} />
          Register Evidence for Case
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
                Computed Hash: {verifyResult.computed_hash}
              </div>
            )}
          </div>
        </div>
      )}

      <div className="stats-grid" style={{ marginBottom: "24px" }}>
        <div className="stat-card">
          <div className="stat-content">
            <span>Case Status</span>
            <strong>{caseData.status}</strong>
            <small>Created {new Date(caseData.created_at).toLocaleDateString()}</small>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-content">
            <span>Lead Investigator</span>
            <strong>{caseData.creator?.username || "Investigator"}</strong>
            <small>Role: {caseData.creator?.role || "Investigator"}</small>
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-content">
            <span>Evidence Items</span>
            <strong>{evidenceList.length}</strong>
            <small>{evidenceList.filter((e) => e.status === "Verified").length} Hash Verified</small>
          </div>
        </div>
      </div>

      <div className="tab-navigation">
        <button
          className={`tab-button ${activeTab === "evidence" ? "active" : ""}`}
          onClick={() => setActiveTab("evidence")}
        >
          Evidence Items ({evidenceList.length})
        </button>
      </div>

      {activeTab === "evidence" && (
        <div className="panel">
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Evidence ID</th>
                  <th>Type</th>
                  <th>Description</th>
                  <th>Device Serial</th>
                  <th>Cryptographic Hash</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {evidenceList.length === 0 ? (
                  <tr>
                    <td colSpan={7} style={{ textAlign: "center", padding: "30px" }}>
                      No evidence registered for this case yet. Click "Register Evidence" to add digital evidence.
                    </td>
                  </tr>
                ) : (
                  evidenceList.map((item) => (
                    <tr key={item.id}>
                      <td>
                        <div className="evidence-name">
                          <div className="file-icon"><Archive size={16} /></div>
                          <strong>{item.evidence_id}</strong>
                        </div>
                      </td>
                      <td>{item.evidence_type}</td>
                      <td>{item.description || "-"}</td>
                      <td>{item.device_identifier || "-"}</td>
                      <td>
                        <div className="hash">
                          <Hash size={14} />
                          {item.hash_value ? `${item.hash_value.substring(0, 14)}...` : "Not calculated"}
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
                            title="Upload File & Calculate Hash"
                            onClick={() => onOpenUploadModal(item)}
                          >
                            <Upload size={14} /> Upload
                          </button>
                          <button
                            className="primary-button"
                            style={{ padding: "4px 8px", fontSize: "10px" }}
                            disabled={verifyingId === item.evidence_id || !item.hash_value}
                            onClick={() => handleVerifyHash(item.evidence_id)}
                          >
                            <ShieldCheck size={14} />
                            {verifyingId === item.evidence_id ? "Verifying..." : "Verify Hash"}
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
      )}
    </div>
  );
};
