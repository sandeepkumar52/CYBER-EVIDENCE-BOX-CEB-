import React, { useState } from "react";
import { Upload, X } from "lucide-react";
import api from "../services/api";
import type { Evidence } from "../types";

interface Props {
  isOpen: boolean;
  evidence: Evidence | null;
  onClose: () => void;
  onUploadSuccess: (updatedEv: Evidence) => void;
}

export const UploadEvidenceModal: React.FC<Props> = ({
  isOpen,
  evidence,
  onClose,
  onUploadSuccess,
}) => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  if (!isOpen || !evidence) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile) {
      setError("Please select a file to upload.");
      return;
    }

    setError(null);
    setSubmitting(true);

    const formData = new FormData();
    formData.append("file", selectedFile);

    try {
      const response = await api.post<Evidence>(
        `/evidence/${evidence.evidence_id}/upload`,
        formData,
        {
          headers: {
            "Content-Type": "multipart/form-data",
          },
        }
      );
      onUploadSuccess(response.data);
      onClose();
    } catch (err: any) {
      if (err.response && err.response.data && err.response.data.detail) {
        setError(err.response.data.detail);
      } else {
        setError("Failed to upload evidence file.");
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="modal-overlay">
      <div className="modal-content">
        <div className="modal-header">
          <h3>Upload Evidence File ({evidence.evidence_id})</h3>
          <button className="modal-close" onClick={onClose}>
            <X size={18} />
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="modal-body">
            {error && <div className="error-banner">{error}</div>}

            <p className="muted" style={{ marginBottom: "16px" }}>
              Upload binary image or raw evidence file for <strong>{evidence.evidence_id}</strong>.
              The system will automatically store the file in secure storage and calculate its{" "}
              <strong>{evidence.hash_algorithm || "SHA-256"}</strong> hash.
            </p>

            <div className="form-group">
              <label>Select Evidence File</label>
              <input
                type="file"
                className="form-control"
                onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
                required
              />
            </div>

            {selectedFile && (
              <div
                style={{
                  padding: "10px",
                  background: "#101722",
                  borderRadius: "6px",
                  fontSize: "11px",
                  color: "#9ab0ce",
                  display: "flex",
                  alignItems: "center",
                  gap: "8px",
                }}
              >
                <Upload size={16} />
                <span>
                  Ready to upload <strong>{selectedFile.name}</strong> ({(selectedFile.size / 1024 / 1024).toFixed(2)} MB)
                </span>
              </div>
            )}
          </div>

          <div className="modal-footer">
            <button type="button" className="secondary-button" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="primary-button" disabled={submitting || !selectedFile}>
              {submitting ? "Hashing & Storing..." : "Upload & Hash File"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
