import { useEffect, useState } from "react";
import * as preferencesApi from "../api/preferences";
import * as usersApi from "../api/users";
import { useAuth } from "../auth/AuthContext";
import { ApiError } from "../api/client";
import type { DoctorPreference, User } from "../types";

export function PreferencesSettingsPage() {
  const { user } = useAuth();
  const isAdmin = user?.role === "SUPER_ADMIN";

  const [providers, setProviders] = useState<User[]>([]);
  const [selectedProviderId, setSelectedProviderId] = useState<string>(user?.id ?? "");
  const [preferences, setPreferences] = useState<DoctorPreference[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      if (isAdmin) {
        const all = await usersApi.listUsers();
        const provs = all.filter((u) => u.role === "PROVIDER");
        setProviders(provs);
        if (provs.length > 0) setSelectedProviderId(provs[0].id);
      }
    })();
  }, [isAdmin]);

  async function refresh(providerId: string) {
    if (!providerId) {
      setPreferences([]);
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      setPreferences(await preferencesApi.listPreferences(isAdmin ? providerId : undefined));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load preferences");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh(selectedProviderId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedProviderId]);

  async function handleCreate(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = new FormData(e.currentTarget);
    try {
      await preferencesApi.createPreference({
        trigger_phrase: String(form.get("trigger_phrase")),
        instruction: String(form.get("instruction")),
        provider_id: isAdmin ? selectedProviderId : undefined,
      });
      (e.target as HTMLFormElement).reset();
      refresh(selectedProviderId);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to create preference");
    }
  }

  async function toggleActive(pref: DoctorPreference) {
    try {
      await preferencesApi.updatePreference(pref.id, { is_active: !pref.is_active });
      refresh(selectedProviderId);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to update preference");
    }
  }

  async function handleDelete(pref: DoctorPreference) {
    try {
      await preferencesApi.deletePreference(pref.id);
      refresh(selectedProviderId);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to delete preference");
    }
  }

  return (
    <div className="page stack">
      <h1 style={{ fontSize: 22 }}>Doctor preferences</h1>
      <p style={{ fontSize: 13, color: "var(--color-text-muted)", marginTop: -8 }}>
        Rules like "when the patient mentions tooth pain, always suggest a CBCT scan" are applied
        automatically the next time a note is generated for this provider.
      </p>

      {isAdmin && (
        <div className="row">
          <label style={{ fontSize: 13 }}>Provider:</label>
          <select
            className="input"
            style={{ width: 240 }}
            value={selectedProviderId}
            onChange={(e) => setSelectedProviderId(e.target.value)}
          >
            {providers.map((p) => (
              <option key={p.id} value={p.id}>
                {p.full_name}
              </option>
            ))}
          </select>
        </div>
      )}

      {error && <div className="error-text">{error}</div>}

      <form className="card row" onSubmit={handleCreate} style={{ flexWrap: "wrap" }}>
        <input
          className="input"
          name="trigger_phrase"
          placeholder='Trigger phrase, e.g. "tooth pain"'
          required
          style={{ width: 260 }}
        />
        <input
          className="input"
          name="instruction"
          placeholder='Instruction, e.g. "always suggest a CBCT scan"'
          required
          style={{ width: 320 }}
        />
        <button className="btn btn-primary" type="submit" disabled={isAdmin && !selectedProviderId}>
          Add rule
        </button>
      </form>

      <div className="card">
        {loading ? (
          <div>Loading…</div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>When transcript mentions</th>
                <th>Then</th>
                <th>Status</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {preferences.map((p) => (
                <tr key={p.id}>
                  <td>{p.trigger_phrase}</td>
                  <td>{p.instruction}</td>
                  <td>{p.is_active ? "Active" : "Inactive"}</td>
                  <td className="row">
                    <button className="btn" onClick={() => toggleActive(p)}>
                      {p.is_active ? "Disable" : "Enable"}
                    </button>
                    <button className="btn btn-danger" onClick={() => handleDelete(p)}>
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
              {preferences.length === 0 && (
                <tr>
                  <td colSpan={4} style={{ color: "var(--color-text-muted)" }}>
                    No preference rules yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
