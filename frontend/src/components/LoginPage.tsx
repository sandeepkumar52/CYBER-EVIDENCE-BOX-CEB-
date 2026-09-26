import React, { useState } from "react";
import { ShieldCheck } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import api from "../services/api";
import type { AuthResponse } from "../types";

export const LoginPage: React.FC = () => {
  const { login } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);

    try {
      const response = await api.post<AuthResponse>("/auth/login", {
        username,
        password,
      });
      login(response.data.access_token, response.data.user);
    } catch (err: any) {
      if (err.response && err.response.data && err.response.data.detail) {
        setError(err.response.data.detail);
      } else {
        setError("Failed to connect to CEB backend server. Please verify FastAPI is running.");
      }
    } finally {
      setSubmitting(false);
    }
  };

  const handleQuickLogin = async (user: string, pass: string) => {
    setUsername(user);
    setPassword(pass);
    setError(null);
    setSubmitting(true);
    try {
      const response = await api.post<AuthResponse>("/auth/login", {
        username: user,
        password: pass,
      });
      login(response.data.access_token, response.data.user);
    } catch (err: any) {
      setError("Failed to log in with quick credentials");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="login-container">
      <div className="login-card">
        <div className="login-header">
          <div className="login-brand-icon">
            <ShieldCheck size={30} />
          </div>
          <h2>Cyber Evidence Box</h2>
          <p>Digital Forensic Evidence Management Platform</p>
        </div>

        {error && <div className="error-banner">{error}</div>}

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>Username</label>
            <input
              type="text"
              className="form-control"
              placeholder="Enter investigator username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
            />
          </div>

          <div className="form-group">
            <label>Password</label>
            <input
              type="password"
              className="form-control"
              placeholder="Enter password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>

          <button
            type="submit"
            className="primary-button"
            style={{ width: "100%", justifyContent: "center", marginTop: "10px" }}
            disabled={submitting}
          >
            {submitting ? "Authenticating..." : "Sign In to CEB"}
          </button>
        </form>

        <div style={{ marginTop: "24px", paddingTop: "18px", borderTop: "1px solid #1c2736" }}>
          <small style={{ color: "#647387", display: "block", marginBottom: "10px", textAlign: "center" }}>
            Quick Demo Logins
          </small>
          <div style={{ display: "flex", gap: "10px" }}>
            <button
              type="button"
              className="secondary-button"
              style={{ flex: 1 }}
              onClick={() => handleQuickLogin("investigator01", "investigator123")}
            >
              Investigator
            </button>
            <button
              type="button"
              className="secondary-button"
              style={{ flex: 1 }}
              onClick={() => handleQuickLogin("admin", "admin123")}
            >
              Admin
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
