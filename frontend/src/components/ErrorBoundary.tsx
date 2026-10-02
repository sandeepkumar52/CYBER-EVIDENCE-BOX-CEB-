import { Component, type ErrorInfo, type ReactNode } from "react";
import { AlertOctagon, RefreshCw, RotateCcw, LayoutDashboard, ChevronDown, ChevronRight } from "lucide-react";

interface Props {
  children: ReactNode;
  fallbackTitle?: string;
  onReset?: () => void;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
  showDetails: boolean;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
    errorInfo: null,
    showDetails: false,
  };

  public static getDerivedStateFromError(error: Error): Partial<State> {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("[CEB ErrorBoundary] Uncaught component error:", error, errorInfo);
    this.setState({ errorInfo });
  }

  private handleRetry = () => {
    if (this.props.onReset) {
      this.props.onReset();
    }
    this.setState({ hasError: false, error: null, errorInfo: null, showDetails: false });
  };

  private handleReload = () => {
    window.location.reload();
  };

  private handleReturnHome = () => {
    this.setState({ hasError: false, error: null, errorInfo: null, showDetails: false });
    window.location.href = "/";
  };

  public render() {
    if (this.state.hasError) {
      return (
        <div className="ceb-error-boundary-container" style={{
          minHeight: "400px",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          padding: "30px",
          background: "#0d131f",
          color: "#e2e8f0",
          fontFamily: "inherit"
        }}>
          <div style={{
            maxWidth: "600px",
            width: "100%",
            background: "#151d2d",
            border: "1px solid rgba(239, 68, 68, 0.3)",
            borderRadius: "12px",
            padding: "32px",
            boxShadow: "0 20px 40px rgba(0, 0, 0, 0.5)"
          }}>
            <div style={{ display: "flex", alignItems: "center", gap: "16px", marginBottom: "20px" }}>
              <div style={{
                background: "rgba(239, 68, 68, 0.15)",
                color: "#ef4444",
                padding: "12px",
                borderRadius: "10px",
                display: "flex"
              }}>
                <AlertOctagon size={32} />
              </div>
              <div>
                <h3 style={{ margin: 0, fontSize: "1.25rem", color: "#f87171", letterSpacing: "0.5px" }}>
                  CEB APPLICATION ERROR
                </h3>
                <p style={{ margin: "4px 0 0 0", color: "#94a3b8", fontSize: "0.9rem" }}>
                  {this.props.fallbackTitle || "Something went wrong while loading this module."}
                </p>
              </div>
            </div>

            <p style={{ color: "#cbd5e1", fontSize: "0.9rem", lineHeight: "1.5", marginBottom: "24px" }}>
              An unexpected runtime error occurred. Forensic evidence and existing database records remain intact and safe.
            </p>

            {/* ERROR DETAILS ACCORDION */}
            <div style={{
              background: "#0b1019",
              border: "1px solid #1e293b",
              borderRadius: "8px",
              marginBottom: "24px",
              overflow: "hidden"
            }}>
              <button
                type="button"
                onClick={() => this.setState((prev) => ({ showDetails: !prev.showDetails }))}
                style={{
                  width: "100%",
                  padding: "10px 14px",
                  background: "transparent",
                  border: 0,
                  color: "#94a3b8",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  cursor: "pointer",
                  fontSize: "0.82rem",
                  fontWeight: 600
                }}
              >
                <span>TECHNICAL ERROR DETAILS</span>
                {this.state.showDetails ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
              </button>

              {this.state.showDetails && (
                <div style={{
                  padding: "14px",
                  borderTop: "1px solid #1e293b",
                  fontFamily: "Consolas, monospace",
                  fontSize: "0.78rem",
                  color: "#fca5a5",
                  maxHeight: "200px",
                  overflowY: "auto",
                  whiteSpace: "pre-wrap",
                  wordBreak: "break-all"
                }}>
                  <strong>{this.state.error?.toString()}</strong>
                  {this.state.errorInfo?.componentStack && (
                    <div style={{ marginTop: "10px", color: "#94a3b8" }}>
                      {this.state.errorInfo.componentStack}
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* RECOVERY ACTION BUTTONS */}
            <div style={{ display: "flex", flexWrap: "wrap", gap: "10px", justifyContent: "flex-end" }}>
              <button
                onClick={this.handleReturnHome}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "8px",
                  background: "#1e293b",
                  border: "1px solid #334155",
                  color: "#e2e8f0",
                  padding: "10px 16px",
                  borderRadius: "8px",
                  cursor: "pointer",
                  fontSize: "0.88rem",
                  fontWeight: 500
                }}
              >
                <LayoutDashboard size={16} />
                Return to Dashboard
              </button>

              <button
                onClick={this.handleReload}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "8px",
                  background: "#1e293b",
                  border: "1px solid #334155",
                  color: "#e2e8f0",
                  padding: "10px 16px",
                  borderRadius: "8px",
                  cursor: "pointer",
                  fontSize: "0.88rem",
                  fontWeight: 500
                }}
              >
                <RotateCcw size={16} />
                Reload Application
              </button>

              <button
                onClick={this.handleRetry}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "8px",
                  background: "#2563eb",
                  border: "1px solid #3b82f6",
                  color: "#ffffff",
                  padding: "10px 18px",
                  borderRadius: "8px",
                  cursor: "pointer",
                  fontSize: "0.88rem",
                  fontWeight: 600
                }}
              >
                <RefreshCw size={16} />
                Retry
              </button>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
