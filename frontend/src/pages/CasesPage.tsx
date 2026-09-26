import React, { useEffect, useState } from "react";
import { ChevronRight, Clock3, Plus, Search, ShieldEllipsis } from "lucide-react";
import api from "../services/api";
import type { Case } from "../types";

interface Props {
  onNavigate: (page: string, param?: string) => void;
  onOpenCreateCase: () => void;
}

export const CasesPage: React.FC<Props> = ({ onNavigate, onOpenCreateCase }) => {
  const [cases, setCases] = useState<Case[]>([]);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("All");
  const [loading, setLoading] = useState(true);

  const fetchCases = async () => {
    try {
      setLoading(true);
      let url = "/cases?limit=100";
      if (search) url += `&search=${encodeURIComponent(search)}`;
      if (statusFilter !== "All") url += `&status=${encodeURIComponent(statusFilter)}`;

      const response = await api.get<Case[]>(url);
      setCases(response.data);
    } catch (err) {
      console.error("Failed to fetch cases:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCases();
  }, [search, statusFilter]);

  return (
    <div style={{ padding: "30px", maxWidth: "1700px", margin: "auto" }}>
      <div className="welcome-row">
        <div>
          <p className="eyebrow">CASE MANAGEMENT</p>
          <h3>Forensic Cases & Investigations</h3>
          <p className="muted">View and manage registered forensic investigation cases.</p>
        </div>

        <button className="primary-button" onClick={onOpenCreateCase}>
          <Plus size={18} />
          New Investigation Case
        </button>
      </div>

      <div className="search-bar-container">
        <div className="search-input-wrapper">
          <Search size={16} />
          <input
            type="text"
            className="form-control"
            placeholder="Search cases by Case ID, title, or description..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>

        <select
          className="form-control"
          style={{ width: "200px" }}
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
        >
          <option value="All">All Statuses</option>
          <option value="Active">Active</option>
          <option value="Under Investigation">Under Investigation</option>
          <option value="Closed">Closed</option>
          <option value="Archived">Archived</option>
        </select>
      </div>

      <div className="panel">
        <div className="panel-header">
          <h4>Case Directory ({cases.length} cases)</h4>
        </div>

        <div className="case-list">
          {loading ? (
            <div style={{ padding: "30px", textAlign: "center", color: "#647387" }}>
              Loading cases...
            </div>
          ) : cases.length === 0 ? (
            <div style={{ padding: "40px", textAlign: "center", color: "#647387" }}>
              No cases matching your criteria.
            </div>
          ) : (
            cases.map((item) => (
              <div
                className="case-row"
                key={item.id}
                onClick={() => onNavigate("case-details", item.case_id)}
                style={{ cursor: "pointer" }}
              >
                <div className="case-icon">
                  <ShieldEllipsis size={20} />
                </div>

                <div className="case-main">
                  <strong>{item.case_name}</strong>
                  <span>
                    {item.case_id} · Created by {item.creator?.username || "Investigator"}
                  </span>
                  {item.description && (
                    <small style={{ color: "#647387", display: "block", marginTop: "3px" }}>
                      {item.description}
                    </small>
                  )}
                </div>

                <div className="case-evidence">
                  <strong>{item.evidence_count || 0}</strong>
                  <span>evidence</span>
                </div>

                <span className={`status-badge ${item.status.toLowerCase().replace(/\s+/g, "")}`}>
                  <span />
                  {item.status}
                </span>

                <div className="case-updated">
                  <Clock3 size={14} />
                  {new Date(item.created_at).toLocaleDateString()}
                </div>

                <ChevronRight className="row-arrow" size={17} />
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};
