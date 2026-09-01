import { useEffect, useState } from "react";
import * as usersApi from "../api/users";
import type { User, UserRole } from "../types";
import { ApiError } from "../api/client";

export function ClinicAdminDashboard() {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [assignProvider, setAssignProvider] = useState("");
  const [assignAssistant, setAssignAssistant] = useState("");

  async function refresh() {
    setLoading(true);
    try {
      setUsers(await usersApi.listUsers());
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load users");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  async function handleCreate(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = new FormData(e.currentTarget);
    try {
      await usersApi.createUser({
        email: String(form.get("email")),
        password: String(form.get("password")),
        full_name: String(form.get("full_name")),
        role: String(form.get("role")) as UserRole,
      });
      setShowForm(false);
      (e.target as HTMLFormElement).reset();
      refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to create user");
    }
  }

  async function handleAssign(e: React.FormEvent) {
    e.preventDefault();
    if (!assignProvider || !assignAssistant) return;
    try {
      await usersApi.assignAssistant(assignProvider, assignAssistant);
      refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to assign");
    }
  }

  async function toggleActive(u: User) {
    try {
      await usersApi.updateUser(u.id, { is_active: !u.is_active });
      refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to update user");
    }
  }

  if (loading) return <div className="page">Loading…</div>;

  const providers = users.filter((u) => u.role === "PROVIDER");
  const assistants = users.filter((u) => u.role === "ASSISTANT");

  return (
    <div className="page stack">
      <div className="row" style={{ justifyContent: "space-between" }}>
        <h1 style={{ fontSize: 22 }}>Clinic admin</h1>
        <button className="btn btn-primary" onClick={() => setShowForm((v) => !v)}>
          {showForm ? "Cancel" : "+ New user"}
        </button>
      </div>

      {error && <div className="error-text">{error}</div>}

      {showForm && (
        <form className="card row" onSubmit={handleCreate} style={{ flexWrap: "wrap" }}>
          <input className="input" name="full_name" placeholder="Full name" required style={{ width: 180 }} />
          <input className="input" name="email" type="email" placeholder="Email" required style={{ width: 220 }} />
          <input className="input" name="password" type="password" placeholder="Temp password" required style={{ width: 160 }} />
          <select className="input" name="role" style={{ width: 160 }}>
            <option value="PROVIDER">Provider (doctor)</option>
            <option value="ASSISTANT">Assistant</option>
            <option value="SUPER_ADMIN">Super admin</option>
          </select>
          <button className="btn btn-primary" type="submit">
            Create
          </button>
        </form>
      )}

      <div className="card">
        <strong>Users</strong>
        <table>
          <thead>
            <tr>
              <th>Name</th>
              <th>Email</th>
              <th>Role</th>
              <th>Status</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.id}>
                <td>{u.full_name}</td>
                <td>{u.email}</td>
                <td>
                  <span className="badge">{u.role}</span>
                </td>
                <td>{u.is_active ? "Active" : "Inactive"}</td>
                <td>
                  <button className="btn" onClick={() => toggleActive(u)}>
                    {u.is_active ? "Deactivate" : "Activate"}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="card stack">
        <strong>Assign assistant to provider</strong>
        <form className="row" onSubmit={handleAssign}>
          <select className="input" value={assignProvider} onChange={(e) => setAssignProvider(e.target.value)} style={{ width: 220 }}>
            <option value="">Select provider…</option>
            {providers.map((p) => (
              <option key={p.id} value={p.id}>
                {p.full_name}
              </option>
            ))}
          </select>
          <select className="input" value={assignAssistant} onChange={(e) => setAssignAssistant(e.target.value)} style={{ width: 220 }}>
            <option value="">Select assistant…</option>
            {assistants.map((a) => (
              <option key={a.id} value={a.id}>
                {a.full_name}
              </option>
            ))}
          </select>
          <button className="btn btn-primary" type="submit" disabled={!assignProvider || !assignAssistant}>
            Assign
          </button>
        </form>
      </div>
    </div>
  );
}
