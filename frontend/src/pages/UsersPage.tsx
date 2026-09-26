import React, { useEffect, useState } from "react";
import { Plus } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import api from "../services/api";
import type { User, UserRole } from "../types";

export const UsersPage: React.FC = () => {
  const { user: currentUser } = useAuth();
  const [users, setUsers] = useState<User[]>([]);
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<UserRole>("Investigator");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const fetchUsers = async () => {
    try {
      setLoading(true);
      const response = await api.get<User[]>("/users");
      setUsers(response.data);
    } catch (err) {
      console.error("Failed to fetch users:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, []);

  const handleCreateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);
    setSubmitting(true);

    try {
      await api.post("/users", {
        username,
        password,
        role,
      });
      setSuccess(`User '${username}' created successfully.`);
      setUsername("");
      setPassword("");
      fetchUsers();
    } catch (err: any) {
      if (err.response && err.response.data && err.response.data.detail) {
        setError(err.response.data.detail);
      } else {
        setError("Failed to create user.");
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div style={{ padding: "30px", maxWidth: "1700px", margin: "auto" }}>
      <div className="welcome-row">
        <div>
          <p className="eyebrow">ACCESS CONTROL</p>
          <h3>Investigator & User Management</h3>
          <p className="muted">Manage forensic operators, investigators, and system roles.</p>
        </div>
      </div>

      {currentUser?.role === "Admin" && (
        <div className="panel" style={{ marginBottom: "24px", padding: "20px" }}>
          <h4 style={{ margin: "0 0 16px", fontSize: "14px" }}>Register New Investigator Account</h4>

          {error && <div className="error-banner">{error}</div>}
          {success && <div className="success-banner">{success}</div>}

          <form onSubmit={handleCreateUser} style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr auto", gap: "12px", alignItems: "end" }}>
            <div className="form-group" style={{ marginBottom: 0 }}>
              <label>Username</label>
              <input
                type="text"
                className="form-control"
                placeholder="e.g. investigator02"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
              />
            </div>

            <div className="form-group" style={{ marginBottom: 0 }}>
              <label>Password</label>
              <input
                type="password"
                className="form-control"
                placeholder="Initial password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>

            <div className="form-group" style={{ marginBottom: 0 }}>
              <label>Role</label>
              <select
                className="form-control"
                value={role}
                onChange={(e) => setRole(e.target.value as UserRole)}
              >
                <option value="Investigator">Investigator</option>
                <option value="Admin">Admin</option>
                <option value="Viewer">Viewer</option>
              </select>
            </div>

            <button type="submit" className="primary-button" disabled={submitting}>
              <Plus size={16} /> {submitting ? "Creating..." : "Create User"}
            </button>
          </form>
        </div>
      )}

      <div className="panel">
        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>User ID</th>
                <th>Username</th>
                <th>Assigned Role</th>
                <th>Registered Date</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={4} style={{ textAlign: "center", padding: "30px" }}>
                    Loading user directory...
                  </td>
                </tr>
              ) : (
                users.map((u) => (
                  <tr key={u.id}>
                    <td>#{u.id}</td>
                    <td>
                      <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                        <div className="operator-avatar">{u.username.substring(0, 2).toUpperCase()}</div>
                        <strong style={{ color: "#dce6f5" }}>{u.username}</strong>
                      </div>
                    </td>
                    <td>
                      <span className={`status-badge ${u.role === "Admin" ? "active" : "review"}`}>
                        <span />
                        {u.role}
                      </span>
                    </td>
                    <td>{new Date(u.created_at).toLocaleDateString()}</td>
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
