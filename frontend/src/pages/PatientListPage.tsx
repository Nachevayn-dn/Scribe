import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import * as patientsApi from "../api/patients";
import * as usersApi from "../api/users";
import { StartScribeSessionModal } from "../components/encounters/StartScribeSessionModal";
import type { Encounter, Patient, User } from "../types";
import { ApiError } from "../api/client";

export function PatientListPage() {
  const navigate = useNavigate();
  const [patients, setPatients] = useState<Patient[]>([]);
  const [providers, setProviders] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [startingFor, setStartingFor] = useState<Patient | null>(null);

  async function refresh() {
    setLoading(true);
    try {
      const [p, prov] = await Promise.all([patientsApi.listPatients(), usersApi.myAssignedProviders()]);
      setPatients(p);
      setProviders(prov);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load patients");
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
      await patientsApi.createPatient({
        first_name: String(form.get("first_name")),
        last_name: String(form.get("last_name")),
        date_of_birth: String(form.get("date_of_birth")),
        mrn: String(form.get("mrn") || "") || undefined,
        phone: String(form.get("phone") || "") || undefined,
        email: String(form.get("email") || "") || undefined,
      });
      setShowForm(false);
      (e.target as HTMLFormElement).reset();
      refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to create patient");
    }
  }

  function handleStarted(encounter: Encounter) {
    navigate(`/encounters/${encounter.id}`);
  }

  if (loading) return <div className="page">Loading…</div>;

  return (
    <div className="page stack">
      <div className="row" style={{ justifyContent: "space-between" }}>
        <h1 style={{ fontSize: 22 }}>Patients</h1>
        <button className="btn btn-primary" onClick={() => setShowForm((v) => !v)}>
          {showForm ? "Cancel" : "+ New patient"}
        </button>
      </div>

      {error && <div className="error-text">{error}</div>}

      {showForm && (
        <form className="card row" onSubmit={handleCreate} style={{ flexWrap: "wrap" }}>
          <input className="input" name="first_name" placeholder="First name" required style={{ width: 160 }} />
          <input className="input" name="last_name" placeholder="Last name" required style={{ width: 160 }} />
          <input className="input" name="date_of_birth" type="date" required style={{ width: 160 }} />
          <input className="input" name="mrn" placeholder="MRN (optional)" style={{ width: 160 }} />
          <input className="input" name="phone" placeholder="Phone (optional)" style={{ width: 160 }} />
          <input className="input" name="email" placeholder="Email (optional)" style={{ width: 200 }} />
          <button className="btn btn-primary" type="submit">
            Save
          </button>
        </form>
      )}

      <div className="card">
        <table>
          <thead>
            <tr>
              <th>Name</th>
              <th>Date of birth</th>
              <th>MRN</th>
              <th>Phone</th>
              <th>Email</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {patients.map((p) => (
              <tr key={p.id}>
                <td>
                  {p.first_name} {p.last_name}
                </td>
                <td>{p.date_of_birth}</td>
                <td>{p.mrn ?? "—"}</td>
                <td>{p.phone ?? "—"}</td>
                <td>{p.email ?? "—"}</td>
                <td>
                  <button
                    className="btn"
                    disabled={providers.length === 0}
                    onClick={() => setStartingFor(p)}
                    title={providers.length === 0 ? "No doctor available to record for" : undefined}
                  >
                    Start Scribe session
                  </button>
                </td>
              </tr>
            ))}
            {patients.length === 0 && (
              <tr>
                <td colSpan={6} style={{ color: "var(--color-text-muted)" }}>
                  No patients yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {startingFor && (
        <StartScribeSessionModal
          key={startingFor.id}
          patient={startingFor}
          providers={providers}
          onClose={() => setStartingFor(null)}
          onStarted={handleStarted}
        />
      )}
    </div>
  );
}
