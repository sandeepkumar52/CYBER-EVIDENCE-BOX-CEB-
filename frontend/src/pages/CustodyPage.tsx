import React, { useEffect, useState } from "react";
import { PackageSearch } from "lucide-react";
import api from "../services/api";
import type { CustodyEvent, DashboardStats } from "../types";

export const CustodyPage: React.FC = () => {
  const [custodyLogs, setCustodyLogs] = useState<CustodyEvent[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchGlobalCustody = async () => {
    try {
      setLoading(true);
      const response = await api.get<DashboardStats>("/dashboard/stats");
      setCustodyLogs(response.data.recent_custody_events);
    } catch (err) {
      console.error("Failed to fetch chain of custody:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchGlobalCustody();
  }, []);

  return (
    <div style={{ padding: "30px", maxWidth: "1700px", margin: "auto" }}>
      <div className="welcome-row">
        <div>
          <p className="eyebrow">FORENSIC TRACEABILITY</p>
          <h3>Chain of Custody Directory</h3>
          <p className="muted">Immutable chronological log of all evidence transfers, security checks, and handoffs.</p>
        </div>
      </div>

      <div className="panel">
        <div className="panel-header">
          <h4>Chronological Custody Events</h4>
        </div>

        <div className="timeline" style={{ padding: "24px" }}>
          {loading ? (
            <div style={{ padding: "20px", color: "#647387" }}>Loading custody history...</div>
          ) : custodyLogs.length === 0 ? (
            <div style={{ padding: "20px", color: "#647387" }}>No custody events logged yet.</div>
          ) : (
            custodyLogs.map((item) => (
              <div className="timeline-item" key={item.id} style={{ marginBottom: "16px" }}>
                <div className="timeline-icon">
                  <PackageSearch size={16} />
                </div>
                <div className="timeline-content">
                  <strong style={{ fontSize: "12px" }}>{item.action}</strong>
                  <span style={{ fontSize: "10px", color: "#8ca0bb" }}>
                    Location: {item.location || "Digital Vault"} · Operator: {item.user?.username || `User #${item.user_id}`}
                  </span>
                  {item.remarks && (
                    <div style={{ color: "#647387", marginTop: "4px", fontSize: "10px" }}>
                      Remarks: {item.remarks}
                    </div>
                  )}
                  <small>{new Date(item.timestamp).toLocaleString()}</small>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};
