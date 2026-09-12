import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import * as patientsApi from "../api/patients";
import * as usersApi from "../api/users";
import { StartSessionButton } from "../components/encounters/StartSessionButton";
import type { Encounter, Patient, User } from "../types";
import { ApiError } from "../api/client";

export function PatientListPage() {
  const navigate = useNavigate();
  const [patients, setPatients] = useState<Patient[]>([]);
  const [providers, setProviders] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [search, setSearch] = useState("");

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

  const filtered = useMemo(() => {
    const term = search.trim().toLowerCase();
    if (!term) return patients;
    return patients.filter((p) => {
      const fullName = `${p.first_name} ${p.last_name}`.toLowerCase();
      return fullName.includes(term) || p.date_of_birth.includes(term);
    });
  }, [patients, search]);

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

      <input
        className="input"
        placeholder="Search by name or date of birth (YYYY-MM-DD)…"
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        style={{ maxWidth: 360 }}
      />

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
            {filtered.map((p) => (
              <tr key={p.id}>
                <td>
                  <Link to={`/sessions?patient_id=${p.id}`}>
                    {p.first_name} {p.last_name}
                  </Link>
                </td>
                <td>{p.date_of_birth}</td>
                <td>{p.mrn ?? "—"}</td>
                <td>{p.phone ?? "—"}</td>
                <td>{p.email ?? "—"}</td>
                <td>
                  <StartSessionButton patient={p} providers={providers} onStarted={handleStarted} onError={setError} />
                </td>
              </tr>
            ))}
            {filtered.length === 0 && (
              <tr>
                <td colSpan={6} style={{ color: "var(--color-text-muted)" }}>
                  {patients.length === 0 ? "No patients yet." : "No patients match your search."}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
