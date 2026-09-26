import React, { useEffect, useState } from "react";
import { Activity, Search } from "lucide-react";
import api from "../services/api";
import type { AuditLog } from "../types";

export const AuditLogsPage: React.FC = () => {
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);

  const fetchAuditLogs = async () => {
    try {
      setLoading(true);
      let url = "/audit-logs?limit=100";
      if (search) url += `&search=${encodeURIComponent(search)}`;
      const response = await api.get<AuditLog[]>(url);
      setAuditLogs(response.data);
    } catch (err) {
      console.error("Failed to fetch audit logs:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAuditLogs();
  }, [search]);

  return (
    <div style={{ padding: "30px", maxWidth: "1700px", margin: "auto" }}>
      <div className="welcome-row">
        <div>
          <p className="eyebrow">SYSTEM SECURITY</p>
          <h3>Centralized System Audit Logs</h3>
          <p className="muted">Append-only audit tracking of user actions, logins, case edits, and hash operations.</p>
        </div>
      </div>

      <div className="search-bar-container">
        <div className="search-input-wrapper">
          <Search size={16} />
          <input
            type="text"
            className="form-control"
            placeholder="Search audit events or details..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
      </div>

      <div className="panel">
        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>Event Type</th>
                <th>Details</th>
                <th>Operator</th>
                <th>Timestamp</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={4} style={{ textAlign: "center", padding: "30px" }}>
                    Loading audit trail...
                  </td>
                </tr>
              ) : auditLogs.length === 0 ? (
                <tr>
                  <td colSpan={4} style={{ textAlign: "center", padding: "30px" }}>
                    No audit logs matching search query.
                  </td>
                </tr>
              ) : (
                auditLogs.map((log) => (
                  <tr key={log.id}>
                    <td>
                      <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                        <Activity size={16} color="#6198eb" />
                        <strong style={{ color: "#d2dceb", fontSize: "11px" }}>{log.event}</strong>
                      </div>
                    </td>
                    <td>{log.details || "-"}</td>
                    <td>{log.user?.username || (log.user_id ? `User #${log.user_id}` : "System")}</td>
                    <td>{new Date(log.timestamp).toLocaleString()}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
