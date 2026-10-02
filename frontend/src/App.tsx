import React, { useEffect, useState } from "react";
import {
  Activity,
  Database,
  FolderOpen,
  LayoutDashboard,
  LogOut,
  Menu,
  PackageSearch,
  ShieldCheck,
  Users,
  Usb,
  X,
} from "lucide-react";

import { AuthProvider, useAuth } from "./context/AuthContext";
import api from "./services/api";
import type { Case, Evidence } from "./types";

import { CreateCaseModal } from "./components/CreateCaseModal";
import { RegisterEvidenceModal } from "./components/RegisterEvidenceModal";
import { UploadEvidenceModal } from "./components/UploadEvidenceModal";
import { AddCustodyModal } from "./components/AddCustodyModal";
import { LoginPage } from "./components/LoginPage";
import { USBScanModal } from "./components/USBScanModal";
import { ErrorBoundary } from "./components/ErrorBoundary";

import { DashboardPage } from "./pages/DashboardPage";
import { CasesPage } from "./pages/CasesPage";
import { CaseDetailsPage } from "./pages/CaseDetailsPage";
import { EvidencePage } from "./pages/EvidencePage";
import { CustodyPage } from "./pages/CustodyPage";
import { AuditLogsPage } from "./pages/AuditLogsPage";
import { UsersPage } from "./pages/UsersPage";
import { HardwarePage } from "./pages/HardwarePage";

import "./App.css";

const MainApp: React.FC = () => {
  const { user, logout, isAuthenticated, loading } = useAuth();
  const [activePage, setActivePage] = useState<string>("dashboard");
  const [activeParam, setActiveParam] = useState<string | undefined>(undefined);
  const [sidebarOpen, setSidebarOpen] = useState<boolean>(false);
  const [backendStatus, setBackendStatus] = useState<string>("Checking...");
  const [casesList, setCasesList] = useState<Case[]>([]);

  // Modals state
  const [isCreateCaseOpen, setIsCreateCaseOpen] = useState(false);
  const [isRegisterEvidenceOpen, setIsRegisterEvidenceOpen] = useState(false);
  const [registerCaseId, setRegisterCaseId] = useState<number | undefined>(undefined);
  const [uploadEvidenceItem, setUploadEvidenceItem] = useState<Evidence | null>(null);
  const [custodyEvidenceItem, setCustodyEvidenceItem] = useState<Evidence | null>(null);

  useEffect(() => {
    api
      .get("/health")
      .then((res) => setBackendStatus(res.data?.status || "online"))
      .catch(() => setBackendStatus("Offline"));
  }, []);

  const loadAllCases = async () => {
    try {
      const response = await api.get<Case[]>("/cases?limit=100");
      setCasesList(Array.isArray(response.data) ? response.data : []);
    } catch {
      // Ignored if unauthenticated
    }
  };

  useEffect(() => {
    if (isAuthenticated) {
      loadAllCases();
    }
  }, [isAuthenticated]);

  if (loading) {
    return (
      <div className="login-container">
        <div style={{ color: "#70a7ff", fontSize: "14px" }}>Loading Cyber Evidence Box...</div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <LoginPage />;
  }

  const navigateTo = (page: string, param?: string) => {
    setActivePage(page);
    setActiveParam(param);
    setSidebarOpen(false);
  };

  const handleOpenRegisterEvidence = (cId?: number) => {
    setRegisterCaseId(cId);
    setIsRegisterEvidenceOpen(true);
  };

  return (
    <div className="app-shell">
      <USBScanModal />
      {/* SIDEBAR */}
      <aside className={`sidebar ${sidebarOpen ? "sidebar-open" : ""}`}>
        <div className="brand">
          <div className="brand-icon">
            <ShieldCheck size={25} />
          </div>

          <div>
            <h1>CEB</h1>
            <span>Cyber Evidence Box</span>
          </div>

          <button className="mobile-close" onClick={() => setSidebarOpen(false)}>
            <X size={20} />
          </button>
        </div>

        <div className="system-status">
          <span className="status-dot" />
          <div>
            <strong>System {backendStatus === "healthy" ? "Online" : backendStatus}</strong>
            <small>Evidence station ready</small>
          </div>
        </div>

        <nav className="navigation">
          <button
            className={`nav-item ${activePage === "dashboard" ? "active" : ""}`}
            onClick={() => navigateTo("dashboard")}
          >
            <LayoutDashboard size={19} />
            <span>Dashboard</span>
          </button>

          <button
            className={`nav-item ${activePage === "cases" || activePage === "case-details" ? "active" : ""}`}
            onClick={() => navigateTo("cases")}
          >
            <FolderOpen size={19} />
            <span>Cases</span>
          </button>

          <button
            className={`nav-item ${activePage === "evidence" ? "active" : ""}`}
            onClick={() => navigateTo("evidence")}
          >
            <Database size={19} />
            <span>Evidence</span>
          </button>

          <button
            className={`nav-item ${activePage === "custody" ? "active" : ""}`}
            onClick={() => navigateTo("custody")}
          >
            <PackageSearch size={19} />
            <span>Chain of Custody</span>
          </button>

          <div className="nav-section">HARDWARE & SYSTEM</div>

          <button
            className={`nav-item ${activePage === "hardware" ? "active" : ""}`}
            onClick={() => navigateTo("hardware")}
          >
            <Usb size={19} />
            <span>Hardware & USB Storage</span>
          </button>

          <button
            className={`nav-item ${activePage === "audit-logs" ? "active" : ""}`}
            onClick={() => navigateTo("audit-logs")}
          >
            <Activity size={19} />
            <span>Audit Logs</span>
          </button>

          <button
            className={`nav-item ${activePage === "users" ? "active" : ""}`}
            onClick={() => navigateTo("users")}
          >
            <Users size={19} />
            <span>Users</span>
          </button>
        </nav>

        <div className="sidebar-footer">
          <div className="operator-avatar">
            {user?.username ? user.username.substring(0, 2).toUpperCase() : "SK"}
          </div>

          <div className="operator-info">
            <strong>{user?.username || "Investigator"}</strong>
            <span>{user?.role || "User"}</span>
          </div>

          <button
            onClick={logout}
            title="Sign Out"
            style={{ background: "transparent", border: 0, color: "#778396", cursor: "pointer", padding: "4px" }}
          >
            <LogOut size={17} />
          </button>
        </div>
      </aside>

      {sidebarOpen && <div className="sidebar-overlay" onClick={() => setSidebarOpen(false)} />}

      {/* MAIN CONTENT */}
      <main className="main-content">
        <header className="topbar">
          <button className="mobile-menu" onClick={() => setSidebarOpen(true)}>
            <Menu size={23} />
          </button>

          <div className="page-heading">
            <span className="breadcrumb">CEB / Workspace</span>
            <h2>
              {activePage === "dashboard" && "Investigation Dashboard"}
              {activePage === "cases" && "Case Directory"}
              {activePage === "case-details" && `Case: ${activeParam}`}
              {activePage === "evidence" && "Digital Evidence Registry"}
              {activePage === "custody" && "Chain of Custody"}
              {(activePage === "hardware" || activePage === "usb") && "Hardware & USB Storage Management"}
              {activePage === "audit-logs" && "System Audit Trail"}
              {activePage === "users" && "Investigator & User Accounts"}
            </h2>
          </div>

          <div className="topbar-actions">
            <div className="topbar-user">
              <div className="operator-avatar">
                {user?.username ? user.username.substring(0, 2).toUpperCase() : "SK"}
              </div>
              <div>
                <strong>{user?.username || "Investigator"}</strong>
                <small>{user?.role || "User"}</small>
              </div>
            </div>
          </div>
        </header>

        {/* PAGE ROUTING WITH ERROR BOUNDARIES */}
        <ErrorBoundary fallbackTitle={`Error rendering ${activePage} module`}>
          {activePage === "dashboard" && (
            <DashboardPage
              onNavigate={navigateTo}
              onOpenCreateCase={() => setIsCreateCaseOpen(true)}
            />
          )}

          {activePage === "cases" && (
            <CasesPage
              onNavigate={navigateTo}
              onOpenCreateCase={() => setIsCreateCaseOpen(true)}
            />
          )}

          {activePage === "case-details" && activeParam && (
            <CaseDetailsPage
              caseCode={activeParam}
              onNavigate={navigateTo}
              onOpenRegisterEvidence={handleOpenRegisterEvidence}
              onOpenUploadModal={(ev) => setUploadEvidenceItem(ev)}
            />
          )}

          {activePage === "evidence" && (
            <EvidencePage
              cases={casesList}
              onOpenRegisterModal={() => handleOpenRegisterEvidence()}
              onOpenUploadModal={(ev) => setUploadEvidenceItem(ev)}
              onOpenCustodyModal={(ev) => setCustodyEvidenceItem(ev)}
            />
          )}

          {activePage === "custody" && <CustodyPage />}

          {(activePage === "hardware" || activePage === "usb") && <HardwarePage />}

          {activePage === "audit-logs" && <AuditLogsPage />}

          {activePage === "users" && <UsersPage />}
        </ErrorBoundary>
      </main>

      {/* MODAL DIALOGS */}
      <CreateCaseModal
        isOpen={isCreateCaseOpen}
        onClose={() => setIsCreateCaseOpen(false)}
        onCaseCreated={(newCase) => {
          loadAllCases();
          navigateTo("case-details", newCase.case_id);
        }}
      />

      <RegisterEvidenceModal
        isOpen={isRegisterEvidenceOpen}
        cases={casesList}
        selectedCaseId={registerCaseId}
        onClose={() => setIsRegisterEvidenceOpen(false)}
        onEvidenceRegistered={() => {
          loadAllCases();
          if (activePage === "evidence") {
            navigateTo("evidence");
          }
        }}
      />

      <UploadEvidenceModal
        isOpen={!!uploadEvidenceItem}
        evidence={uploadEvidenceItem}
        onClose={() => setUploadEvidenceItem(null)}
        onUploadSuccess={() => {
          if (activePage === "evidence") navigateTo("evidence");
          else if (activePage === "case-details") loadAllCases();
        }}
      />

      <AddCustodyModal
        isOpen={!!custodyEvidenceItem}
        evidence={custodyEvidenceItem}
        onClose={() => setCustodyEvidenceItem(null)}
        onCustodyAdded={() => {
          if (activePage === "custody") navigateTo("custody");
        }}
      />
    </div>
  );
};

function App() {
  return (
    <ErrorBoundary fallbackTitle="Fatal application crash">
      <AuthProvider>
        <MainApp />
      </AuthProvider>
    </ErrorBoundary>
  );
}

export default App;