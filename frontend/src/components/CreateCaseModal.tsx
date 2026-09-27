import React, { useState } from "react";
import { X } from "lucide-react";
import api from "../services/api";
import type { Case } from "../types";

interface Props {
  isOpen: boolean;
  onClose: () => void;
  onCaseCreated: (newCase: Case) => void;
}

export const CreateCaseModal: React.FC<Props> = ({ isOpen, onClose, onCaseCreated }) => {
  const [caseId, setCaseId] = useState(() => `CASE-2026-${Math.floor(100 + Math.random() * 900)}`);
  const [caseName, setCaseName] = useState("");
  const [description, setDescription] = useState("");
  const [status, setStatus] = useState<"Active" | "Under Investigation" | "Closed">("Active");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);

    try {
      const response = await api.post<Case>("/cases", {
        case_id: caseId,
        case_name: caseName,
        description,
        status,
      });
      onCaseCreated(response.data);
      onClose();
    } catch (err: any) {
      if (err.response && err.response.data && err.response.data.detail) {
        setError(err.response.data.detail);
      } else {
        setError("Failed to create case.");
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="modal-overlay">
      <div className="modal-content">
        <div className="modal-header">
          <h3>Create New Forensic Case</h3>
          <button className="modal-close" onClick={onClose}>
            <X size={18} />
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="modal-body">
            {error && <div className="error-banner">{error}</div>}

            <div className="form-group">
              <label>Case Identifier Code</label>
              <input
                type="text"
                className="form-control"
                value={caseId}
                onChange={(e) => setCaseId(e.target.value)}
                required
              />
            </div>

            <div className="form-group">
              <label>Case Title / Name</label>
              <input
                type="text"
                className="form-control"
                placeholder="e.g. Unauthorized System Access Investigation"
                value={caseName}
                onChange={(e) => setCaseName(e.target.value)}
                required
              />
            </div>

            <div className="form-group">
              <label>Status</label>
              <select
                className="form-control"
                value={status}
                onChange={(e) => setStatus(e.target.value as any)}
              >
                <option value="Active">Active</option>
                <option value="Under Investigation">Under Investigation</option>
                <option value="Closed">Closed</option>
              </select>
            </div>

            <div className="form-group">
              <label>Description / Incident Notes</label>
              <textarea
                className="form-control"
                rows={3}
                placeholder="Enter scope and details of investigation..."
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
              {submitting ? "Creating..." : "Create Case"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
