import React, { useState } from "react";
import { X } from "lucide-react";
import api from "../services/api";
import type { Case, Evidence, EvidenceType } from "../types";

interface Props {
  isOpen: boolean;
  cases: Case[];
  selectedCaseId?: number;
  onClose: () => void;
  onEvidenceRegistered: (newEv: Evidence) => void;
}

export const RegisterEvidenceModal: React.FC<Props> = ({
  isOpen,
  cases,
  selectedCaseId,
  onClose,
  onEvidenceRegistered,
}) => {
  const [evidenceId, setEvidenceId] = useState(() => `EVID-2026-${Math.floor(100 + Math.random() * 900)}`);
  const [caseId, setCaseId] = useState<number>(selectedCaseId || (cases[0]?.id ?? 1));
  const [evidenceType, setEvidenceType] = useState<EvidenceType>("Disk Image");
  const [description, setDescription] = useState("");
  const [deviceIdentifier, setDeviceIdentifier] = useState("");
  const [hashAlgorithm, setHashAlgorithm] = useState("SHA-256");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);

    try {
      const response = await api.post<Evidence>("/evidence", {
        evidence_id: evidenceId,
        case_id: Number(caseId),
        evidence_type: evidenceType,
        description,
        device_identifier: deviceIdentifier,
        hash_algorithm: hashAlgorithm,
      });
      onEvidenceRegistered(response.data);
      onClose();
    } catch (err: any) {
      if (err.response && err.response.data && err.response.data.detail) {
        setError(err.response.data.detail);
      } else {
        setError("Failed to register evidence.");
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="modal-overlay">
      <div className="modal-content">
        <div className="modal-header">
          <h3>Register Digital Evidence</h3>
          <button className="modal-close" onClick={onClose}>
            <X size={18} />
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="modal-body">
            {error && <div className="error-banner">{error}</div>}

            <div className="form-group">
              <label>Evidence Identifier Code</label>
              <input
                type="text"
                className="form-control"
                value={evidenceId}
                onChange={(e) => setEvidenceId(e.target.value)}
                required
              />
            </div>

            <div className="form-group">
              <label>Associated Case</label>
              <select
                className="form-control"
                value={caseId}
                onChange={(e) => setCaseId(Number(e.target.value))}
                required
              >
                {cases.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.case_id} — {c.case_name}
                  </option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label>Evidence Type</label>
              <select
                className="form-control"
                value={evidenceType}
                onChange={(e) => setEvidenceType(e.target.value as EvidenceType)}
              >
                <option value="Disk Image">Disk Image</option>
                <option value="USB Device">USB Device</option>
                <option value="Memory Dump">Memory Dump</option>
                <option value="Log File">Log File</option>
                <option value="Document">Document</option>
                <option value="Mobile Device">Mobile Device</option>
                <option value="Network Capture">Network Capture</option>
                <option value="Other">Other</option>
              </select>
            </div>

            <div className="form-group">
              <label>Device Identifier / Serial Number</label>
              <input
                type="text"
                className="form-control"
                placeholder="e.g. SanDisk Ultra 64GB SN: 981247"
                value={deviceIdentifier}
                onChange={(e) => setDeviceIdentifier(e.target.value)}
              />
            </div>

            <div className="form-group">
              <label>Hash Algorithm</label>
              <select
                className="form-control"
                value={hashAlgorithm}
                onChange={(e) => setHashAlgorithm(e.target.value)}
              >
                <option value="SHA-256">SHA-256 (Default)</option>
                <option value="SHA-512">SHA-512</option>
              </select>
            </div>

            <div className="form-group">
              <label>Description / Source</label>
              <textarea
                className="form-control"
                rows={2}
                placeholder="Details of evidence acquisition..."
                value={description}
                onChange={(e) => setDescription(e.target.value)}
              />
            </div>
          </div>

          <div className="modal-footer">
            <button type="button" className="secondary-button" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="primary-button" disabled={submitting}>
              {submitting ? "Registering..." : "Register Evidence"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
