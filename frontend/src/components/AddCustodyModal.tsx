import React, { useState } from "react";
import { X } from "lucide-react";
import api from "../services/api";
import type { CustodyEvent, Evidence } from "../types";

interface Props {
  isOpen: boolean;
  evidence: Evidence | null;
  onClose: () => void;
  onCustodyAdded: (newEvent: CustodyEvent) => void;
}

export const AddCustodyModal: React.FC<Props> = ({
  isOpen,
  evidence,
  onClose,
  onCustodyAdded,
}) => {
  const [action, setAction] = useState("Evidence Transferred");
  const [location, setLocation] = useState("Digital Forensic Lab Locker A-04");
  const [remarks, setRemarks] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  if (!isOpen || !evidence) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);

    try {
      const response = await api.post<CustodyEvent>(
        `/evidence/${evidence.evidence_id}/custody`,
        {
          action,
          location,
          remarks,
        }
      );
      onCustodyAdded(response.data);
      onClose();
    } catch (err: any) {
      if (err.response && err.response.data && err.response.data.detail) {
        setError(err.response.data.detail);
      } else {
        setError("Failed to add custody event.");
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="modal-overlay">
      <div className="modal-content">
        <div className="modal-header">
          <h3>Log Chain of Custody Event</h3>
          <button className="modal-close" onClick={onClose}>
            <X size={18} />
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="modal-body">
            {error && <div className="error-banner">{error}</div>}

            <p className="muted" style={{ marginBottom: "16px" }}>
              Target Evidence: <strong>{evidence.evidence_id}</strong> ({evidence.evidence_type})
            </p>

            <div className="form-group">
              <label>Custody Action</label>
              <select
                className="form-control"
                value={action}
                onChange={(e) => setAction(e.target.value)}
              >
                <option value="Evidence Transferred">Evidence Transferred</option>
                <option value="Evidence Secured">Evidence Secured</option>
                <option value="Evidence Checked Out for Analysis">Checked Out for Analysis</option>
                <option value="Evidence Returned to Locker">Returned to Locker</option>
                <option value="Court Presentation">Court Presentation</option>
                <option value="Evidence Archived">Evidence Archived</option>
              </select>
            </div>

            <div className="form-group">
              <label>Physical / Digital Location</label>
              <input
                type="text"
                className="form-control"
                placeholder="e.g. Evidence Locker #B-12, Lab Workstation 02"
                value={location}
                onChange={(e) => setLocation(e.target.value)}
              />
            </div>

            <div className="form-group">
              <label>Remarks & Justification</label>
              <textarea
                className="form-control"
                rows={3}
                placeholder="Notes on transfer reason, seal numbers, or condition..."
                value={remarks}
                onChange={(e) => setRemarks(e.target.value)}
              />
            </div>
          </div>

          <div className="modal-footer">
            <button type="button" className="secondary-button" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="primary-button" disabled={submitting}>
              {submitting ? "Logging..." : "Log Custody Event"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
