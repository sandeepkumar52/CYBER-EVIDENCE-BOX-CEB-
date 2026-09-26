import React, { useEffect, useState } from "react";
import {
  Activity,
  Archive,
  ArrowUpRight,
  BadgeCheck,
  ChevronRight,
  CircleCheck,
  Clock3,
  Database,
  Fingerprint,
  FolderOpen,
  HardDrive,
  Hash,
  LockKeyhole,
  Radio,
  ShieldEllipsis,
  Usb,
} from "lucide-react";
import api from "../services/api";
import type { Case, DashboardStats, Evidence } from "../types";

interface Props {
  onNavigate: (page: string, param?: string) => void;
  onOpenCreateCase: () => void;
}

export const DashboardPage: React.FC<Props> = ({ onNavigate, onOpenCreateCase }) => {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [cases, setCases] = useState<Case[]>([]);
  const [evidenceList, setEvidenceList] = useState<Evidence[]>([]);

  const loadDashboardData = async () => {
    try {
      const [statsRes, casesRes, evidenceRes] = await Promise.all([
        api.get<DashboardStats>("/dashboard/stats"),
        api.get<Case[]>("/cases?limit=5"),
        api.get<Evidence[]>("/evidence?limit=5"),
      ]);
      setStats(statsRes.data);
      setCases(casesRes.data);
      setEvidenceList(evidenceRes.data);
    } catch (err) {
      console.error("Failed to load dashboard statistics:", err);
    }
  };

  useEffect(() => {
    loadDashboardData();
  }, []);

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return "0 MB";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB", "GB", "TB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
  };

  return (
    <section className="dashboard">
      <div className="welcome-row">
        <div>
          <p className="eyebrow">FORENSIC WORKSPACE</p>
          <h3>Forensic Overview & System Status</h3>
          <p className="muted">
            Real-time evidence management, cryptographic integrity verification, and audit trace.
          </p>
        </div>

        <button className="primary-button" onClick={onOpenCreateCase}>
          <FolderOpen size={18} />
          Create New Case
        </button>
      </div>

      <section className="stats-grid">
        <div className="stat-card" onClick={() => onNavigate("cases")} style={{ cursor: "pointer" }}>
          <div className="stat-icon">
            <FolderOpen size={21} />
          </div>
          <div className="stat-content">
            <span>Active Cases</span>
            <strong>{stats ? stats.active_cases : "-"}</strong>
            <small>{stats ? `${stats.total_cases} total registered` : "Loading..."}</small>
          </div>
          <ArrowUpRight className="stat-arrow" size={17} />
        </div>

        <div className="stat-card" onClick={() => onNavigate("evidence")} style={{ cursor: "pointer" }}>
          <div className="stat-icon">
            <Database size={21} />
          </div>
          <div className="stat-content">
            <span>Evidence Items</span>
            <strong>{stats ? stats.total_evidence : "-"}</strong>
            <small>{stats ? `${stats.verified_evidence} verified` : "Loading..."}</small>
          </div>
          <ArrowUpRight className="stat-arrow" size={17} />
        </div>

        <div className="stat-card" onClick={() => onNavigate("evidence")} style={{ cursor: "pointer" }}>
          <div className="stat-icon">
            <BadgeCheck size={21} />
          </div>
          <div className="stat-content">
            <span>Integrity Verified</span>
            <strong>{stats ? stats.verified_evidence : "-"}</strong>
            <small>
              {stats && stats.total_evidence > 0
                ? `${((stats.verified_evidence / stats.total_evidence) * 100).toFixed(1)}% verified`
                : "0% verified"}
            </small>
          </div>
          <ArrowUpRight className="stat-arrow" size={17} />
        </div>

        <div className="stat-card">
          <div className="stat-icon">
            <HardDrive size={21} />
          </div>
          <div className="stat-content">
            <span>Evidence Vault Storage</span>
            <strong>{stats ? formatBytes(stats.storage_used_bytes) : "-"}</strong>
            <small>Controlled Local Storage</small>
          </div>
          <ArrowUpRight className="stat-arrow" size={17} />
        </div>
      </section>

      <section className="content-grid">
        <div className="panel cases-panel">
          <div className="panel-header">
            <div>
              <h4>Active Investigations</h4>
              <p>Recently updated forensic cases</p>
            </div>
            <button className="panel-action" onClick={() => onNavigate("cases")}>
              View all <ChevronRight size={15} />
            </button>
          </div>

          <div className="case-list">
            {cases.length === 0 ? (
              <div style={{ padding: "30px", textAlign: "center", color: "#647387" }}>
                No active cases found in the database.
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
                      {item.case_id} · {item.creator?.username || "Investigator"}
                    </span>
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

        <div className="panel system-panel">
          <div className="panel-header">
            <div>
              <h4>Evidence Station</h4>
              <p>Hardware & System Interface</p>
            </div>
          </div>

          <div className="hardware-status">
            <div className="hardware-item">
              <div className="hardware-icon"><Radio size={19} /></div>
              <div><strong>Raspberry Pi Interface</strong><span>Hardware abstraction ready</span></div>
              <span className="hardware-dot" />
            </div>

            <div className="hardware-item">
              <div className="hardware-icon"><HardDrive size={19} /></div>
              <div><strong>Vault Storage Path</strong><span>storage/evidence/</span></div>
              <span className="hardware-dot" />
            </div>

            <div className="hardware-item">
              <div className="hardware-icon"><Usb size={19} /></div>
              <div><strong>Write Blocker API</strong><span>Storage layer protected</span></div>
              <span className="hardware-dot" />
            </div>

            <div className="hardware-item">
              <div className="hardware-icon"><Fingerprint size={19} /></div>
              <div><strong>Cryptographic Hashing</strong><span>SHA-256 Engine Active</span></div>
              <span className="hardware-dot" />
            </div>
          </div>

          <div className="tamper-card">
            <div className="tamper-icon"><LockKeyhole size={18} /></div>
            <div>
              <strong>Tamper Protection Active</strong>
              <span>Forensic chain of custody enforced</span>
            </div>
            <CircleCheck size={20} />
          </div>
        </div>
      </section>

      <section className="content-grid lower-grid">
        <div className="panel evidence-panel">
          <div className="panel-header">
            <div>
              <h4>Recent Evidence Registered</h4>
              <p>Latest registered evidence items</p>
            </div>
            <button className="panel-action" onClick={() => onNavigate("evidence")}>
              View evidence <ChevronRight size={15} />
            </button>
          </div>

          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Evidence</th>
                  <th>Type</th>
                  <th>Size</th>
                  <th>Cryptographic Hash</th>
                  <th>Integrity</th>
                </tr>
              </thead>
              <tbody>
                {evidenceList.length === 0 ? (
                  <tr>
                    <td colSpan={5} style={{ textAlign: "center", padding: "20px" }}>
                      No evidence registered yet.
                    </td>
                  </tr>
                ) : (
                  evidenceList.map((item) => (
                    <tr key={item.id}>
                      <td>
                        <div className="evidence-name">
                          <div className="file-icon"><Archive size={16} /></div>
                          <div>
                            <strong>{item.evidence_id}</strong>
                            <span>{item.description || item.evidence_type}</span>
                          </div>
                        </div>
                      </td>
                      <td>{item.evidence_type}</td>
                      <td>{item.file_size_bytes ? formatBytes(item.file_size_bytes) : "N/A"}</td>
                      <td>
                        <div className="hash">
                          <Hash size={14} />
                          {item.hash_value ? `${item.hash_value.substring(0, 12)}...` : "Not calculated"}
                        </div>
                      </td>
                      <td>
                        <span className={`integrity ${item.status === "Verified" ? "verified" : "processing"}`}>
                          {item.status === "Verified" ? <CircleCheck size={14} /> : <Activity size={14} />}
                          {item.status}
                        </span>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

        <div className="panel activity-panel">
          <div className="panel-header">
            <div>
              <h4>Chain of Custody Activity</h4>
              <p>Recent evidence transfers & actions</p>
            </div>
            <button className="panel-action" onClick={() => onNavigate("custody")}>
              View log <ChevronRight size={15} />
            </button>
          </div>

          <div className="timeline">
            {stats && stats.recent_custody_events.length > 0 ? (
              stats.recent_custody_events.map((event) => (
                <div className="timeline-item" key={event.id}>
                  <div className="timeline-icon"><Hash size={16} /></div>
                  <div className="timeline-content">
                    <strong>{event.action}</strong>
                    <span>{event.remarks || `Evidence ID: ${event.evidence_id}`}</span>
                    <small>{new Date(event.timestamp).toLocaleString()}</small>
                  </div>
                </div>
              ))
            ) : (
              <p style={{ color: "#647387", padding: "15px", fontSize: "11px" }}>No custody events logged.</p>
            )}
          </div>
        </div>
      </section>
    </section>
  );
};
