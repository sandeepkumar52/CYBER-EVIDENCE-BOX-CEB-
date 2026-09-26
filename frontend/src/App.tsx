import {
  Activity,
  Archive,
  ArrowUpRight,
  BadgeCheck,
  Bell,
  
  Camera,
  ChevronRight,
  CircleCheck,
  Clock3,
  Database,
  FileSearch,
  Fingerprint,
  FolderOpen,
  HardDrive,
  Hash,
  LayoutDashboard,
  LockKeyhole,
  Menu,
  
  PackageSearch,
  Radio,
  Search,
  Settings,
  ShieldCheck,
  ShieldEllipsis,
  Usb,
  Users,
  X,
} from "lucide-react";

import { useEffect, useState } from "react";
import api from "./services/api";
import "./App.css";




function App() {
  const [backendStatus, setBackendStatus] = useState("Checking...");
  const [sidebarOpen, setSidebarOpen] = useState(false);
  useEffect(() => {
  api
    .get("/health")
    .then((response) => {
      setBackendStatus(response.data.status);
    })
    .catch(() => {
      setBackendStatus("Offline");
    });
}, []);

type CaseStatus = "Active" | "Review" | "Closed";

interface CaseItem {
  id: string;
  title: string;
  investigator: string;
  evidence: number;
  status: CaseStatus;
  updated: string;
}

interface EvidenceItem {
  id: string;
  name: string;
  type: string;
  size: string;
  hash: string;
  status: "Verified" | "Processing";
}

const cases: CaseItem[] = [
  {
    id: "CASE-2026-001",
    title: "Unauthorized System Access",
    investigator: "S. Kumar",
    evidence: 8,
    status: "Active",
    updated: "12 min ago",
  },
  {
    id: "CASE-2026-002",
    title: "USB Data Exfiltration",
    investigator: "A. Sharma",
    evidence: 5,
    status: "Review",
    updated: "1 hr ago",
  },
  {
    id: "CASE-2026-003",
    title: "Endpoint Investigation",
    investigator: "R. Patel",
    evidence: 12,
    status: "Active",
    updated: "3 hrs ago",
  },
];

const evidence: EvidenceItem[] = [
  {
    id: "EVID-001",
    name: "suspect_drive.E01",
    type: "Disk Image",
    size: "128.4 GB",
    hash: "9b3a...71fc",
    status: "Verified",
  },
  {
    id: "EVID-002",
    name: "usb_capture.dd",
    type: "USB Image",
    size: "31.8 GB",
    hash: "42ef...a921",
    status: "Verified",
  },
  {
    id: "EVID-003",
    name: "system_logs.zip",
    type: "Archive",
    size: "842 MB",
    hash: "c71d...88ab",
    status: "Processing",
  },
];


  return (
    <div className="app-shell">
      <aside className={`sidebar ${sidebarOpen ? "sidebar-open" : ""}`}>
        <div className="brand">
          <div className="brand-icon">
            <ShieldCheck size={25} />
          </div>

          <div>
            <h1>CEB</h1>
            <span>Cyber Evidence Box</span>
          </div>
          <div>
            Backend: {backendStatus}
          </div>

          <button
            className="mobile-close"
            onClick={() => setSidebarOpen(false)}
          >
            <X size={20} />
          </button>
        </div>

        <div className="system-status">
          <span className="status-dot" />
          <div>
            <strong>System Online</strong>
            <small>Evidence station ready</small>
          </div>
        </div>

        <nav className="navigation">
          <NavItem
            icon={<LayoutDashboard size={19} />}
            label="Dashboard"
            active
          />

          <NavItem icon={<FolderOpen size={19} />} label="Cases" />
          <NavItem icon={<Database size={19} />} label="Evidence" />
          <NavItem icon={<Usb size={19} />} label="Acquisition" />
          <NavItem icon={<PackageSearch size={19} />} label="Chain of Custody" />
          <NavItem icon={<FileSearch size={19} />} label="Reports" />

          <div className="nav-section">SYSTEM</div>

          <NavItem icon={<Activity size={19} />} label="Audit Logs" />
          <NavItem icon={<Users size={19} />} label="Users" />
          <NavItem icon={<Settings size={19} />} label="Settings" />
        </nav>

        <div className="sidebar-footer">
          <div className="operator-avatar">SK</div>

          <div className="operator-info">
            <strong>S. Kumar</strong>
            <span>Forensic Operator</span>
          </div>

          <ChevronRight size={17} />
        </div>
      </aside>

      {sidebarOpen && (
        <div
          className="sidebar-overlay"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      <main className="main-content">
        <header className="topbar">
          <button
            className="mobile-menu"
            onClick={() => setSidebarOpen(true)}
          >
            <Menu size={23} />
          </button>

          <div className="page-heading">
            <span className="breadcrumb">CEB / Workspace</span>
            <h2>Investigation Dashboard</h2>
          </div>

          <div className="topbar-actions">
            <button className="icon-button">
              <Search size={19} />
            </button>

            <button className="icon-button notification">
              <Bell size={19} />
              <span />
            </button>

            <div className="topbar-user">
              <div className="operator-avatar">SK</div>
              <div>
                <strong>S. Kumar</strong>
                <small>Operator</small>
              </div>
            </div>
          </div>
        </header>

        <section className="dashboard">
          <div className="welcome-row">
            <div>
              <p className="eyebrow">FORENSIC WORKSPACE</p>
              <h3>Good morning, Sandeep.</h3>
              <p className="muted">
                Monitor investigations, evidence integrity and system status.
              </p>
            </div>

            <button className="primary-button">
              <FolderOpen size={18} />
              Create New Case
            </button>
          </div>

          <section className="stats-grid">
            <StatCard
              icon={<FolderOpen size={21} />}
              label="Active Cases"
              value="12"
              change="+3 this month"
            />

            <StatCard
              icon={<Database size={21} />}
              label="Evidence Items"
              value="47"
              change="+8 this week"
            />

            <StatCard
              icon={<BadgeCheck size={21} />}
              label="Verified Evidence"
              value="44"
              change="93.6% verified"
            />

            <StatCard
              icon={<HardDrive size={21} />}
              label="Storage Used"
              value="426 GB"
              change="of 1 TB available"
            />
          </section>

          <section className="content-grid">
            <div className="panel cases-panel">
              <PanelHeader
                title="Active Investigations"
                subtitle="Recently updated cases"
                action="View all"
              />

              <div className="case-list">
                {cases.map((item) => (
                  <div className="case-row" key={item.id}>
                    <div className="case-icon">
                      <ShieldEllipsis size={20} />
                    </div>

                    <div className="case-main">
                      <strong>{item.title}</strong>
                      <span>
                        {item.id} · {item.investigator}
                      </span>
                    </div>

                    <div className="case-evidence">
                      <strong>{item.evidence}</strong>
                      <span>evidence</span>
                    </div>

                    <StatusBadge status={item.status} />

                    <div className="case-updated">
                      <Clock3 size={14} />
                      {item.updated}
                    </div>

                    <ChevronRight className="row-arrow" size={17} />
                  </div>
                ))}
              </div>
            </div>

            <div className="panel system-panel">
              <PanelHeader
                title="Evidence Station"
                subtitle="Hardware status"
              />

              <div className="hardware-status">
                <HardwareItem
                  icon={<Radio size={19} />}
                  label="Raspberry Pi"
                  status="Online"
                />

                <HardwareItem
                  icon={<HardDrive size={19} />}
                  label="NVMe Storage"
                  status="Mounted"
                />

                <HardwareItem
                  icon={<Usb size={19} />}
                  label="Write Blocker"
                  status="Protected"
                />

                <HardwareItem
                  icon={<Fingerprint size={19} />}
                  label="Authentication"
                  status="Ready"
                />

                <HardwareItem
                  icon={<Camera size={19} />}
                  label="Evidence Camera"
                  status="Ready"
                />
              </div>

              <div className="tamper-card">
                <div className="tamper-icon">
                  <LockKeyhole size={18} />
                </div>

                <div>
                  <strong>Tamper protection active</strong>
                  <span>No security events detected</span>
                </div>

                <CircleCheck size={20} />
              </div>
            </div>
          </section>

          <section className="content-grid lower-grid">
            <div className="panel evidence-panel">
              <PanelHeader
                title="Recent Evidence"
                subtitle="Latest registered evidence"
                action="View evidence"
              />

              <div className="table-wrapper">
                <table>
                  <thead>
                    <tr>
                      <th>Evidence</th>
                      <th>Type</th>
                      <th>Size</th>
                      <th>SHA-256</th>
                      <th>Integrity</th>
                    </tr>
                  </thead>

                  <tbody>
                    {evidence.map((item) => (
                      <tr key={item.id}>
                        <td>
                          <div className="evidence-name">
                            <div className="file-icon">
                              <Archive size={16} />
                            </div>

                            <div>
                              <strong>{item.name}</strong>
                              <span>{item.id}</span>
                            </div>
                          </div>
                        </td>

                        <td>{item.type}</td>
                        <td>{item.size}</td>

                        <td>
                          <div className="hash">
                            <Hash size={14} />
                            {item.hash}
                          </div>
                        </td>

                        <td>
                          <span
                            className={`integrity ${
                              item.status === "Verified"
                                ? "verified"
                                : "processing"
                            }`}
                          >
                            {item.status === "Verified" ? (
                              <CircleCheck size={14} />
                            ) : (
                              <Activity size={14} />
                            )}

                            {item.status}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            <div className="panel activity-panel">
              <PanelHeader
                title="Chain of Custody"
                subtitle="Latest activity"
                action="View log"
              />

              <div className="timeline">
                <TimelineItem
                  icon={<Hash size={16} />}
                  title="Evidence hash verified"
                  description="EVID-001 · SHA-256"
                  time="12 min ago"
                />

                <TimelineItem
                  icon={<LockKeyhole size={16} />}
                  title="Evidence secured"
                  description="EVID-002 · Storage vault"
                  time="31 min ago"
                />

                <TimelineItem
                  icon={<Usb size={16} />}
                  title="Acquisition completed"
                  description="CASE-2026-003"
                  time="1 hr ago"
                />

                <TimelineItem
                  icon={<Users size={16} />}
                  title="Evidence transferred"
                  description="A. Sharma → S. Kumar"
                  time="2 hrs ago"
                />
              </div>
            </div>
          </section>

          <footer className="dashboard-footer">
            <div>
              <span className="footer-indicator" />
              All critical systems operational
            </div>

            <span>CEB v0.1.0 · Forensic Evidence Platform</span>
          </footer>
        </section>
      </main>
    </div>
  );
}

function NavItem({
  icon,
  label,
  active = false,
}: {
  icon: React.ReactNode;
  label: string;
  active?: boolean;
}) {
  return (
    <button className={`nav-item ${active ? "active" : ""}`}>
      {icon}
      <span>{label}</span>
    </button>
  );
}

function StatCard({
  icon,
  label,
  value,
  change,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  change: string;
}) {
  return (
    <div className="stat-card">
      <div className="stat-icon">{icon}</div>

      <div className="stat-content">
        <span>{label}</span>
        <strong>{value}</strong>
        <small>{change}</small>
      </div>

      <ArrowUpRight className="stat-arrow" size={17} />
    </div>
  );
}

function PanelHeader({
  title,
  subtitle,
  action,
}: {
  title: string;
  subtitle: string;
  action?: string;
}) {
  return (
    <div className="panel-header">
      <div>
        <h4>{title}</h4>
        <p>{subtitle}</p>
      </div>

      {action && (
        <button className="panel-action">
          {action}
          <ChevronRight size={15} />
        </button>
      )}
    </div>
  );
}

function StatusBadge({ status }: { status: CaseStatus }) {
  return (
    <span className={`status-badge ${status.toLowerCase()}`}>
      <span />
      {status}
    </span>
  );
}

function HardwareItem({
  icon,
  label,
  status,
}: {
  icon: React.ReactNode;
  label: string;
  status: string;
}) {
  return (
    <div className="hardware-item">
      <div className="hardware-icon">{icon}</div>

      <div>
        <strong>{label}</strong>
        <span>{status}</span>
      </div>

      <span className="hardware-dot" />
    </div>
  );
}

function TimelineItem({
  icon,
  title,
  description,
  time,
}: {
  icon: React.ReactNode;
  title: string;
  description: string;
  time: string;
}) {
  return (
    <div className="timeline-item">
      <div className="timeline-icon">{icon}</div>

      <div className="timeline-content">
        <strong>{title}</strong>
        <span>{description}</span>
        <small>{time}</small>
      </div>
    </div>
  );
}

export default App;