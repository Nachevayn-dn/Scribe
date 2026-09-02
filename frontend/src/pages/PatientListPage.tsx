import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import * as patientsApi from "../api/patients";
import * as usersApi from "../api/users";
import * as encountersApi from "../api/encounters";
import { Modal } from "../components/common/Modal";
import { EU_LANGUAGES } from "../data/languages";
import type { Patient, User } from "../types";
import { ApiError } from "../api/client";

export function PatientListPage() {
  const navigate = useNavigate();
  const [patients, setPatients] = useState<Patient[]>([]);
  const [providers, setProviders] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [startingFor, setStartingFor] = useState<Patient | null>(null);
  const [selectedProviderId, setSelectedProviderId] = useState("");
  const [selectedLanguage, setSelectedLanguage] = useState(EU_LANGUAGES[0].code);
  const [starting, setStarting] = useState(false);

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
      });
      setShowForm(false);
      (e.target as HTMLFormElement).reset();
      refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to create patient");
    }
  }

  function openStartEncounter(patient: Patient) {
    setStartingFor(patient);
    setSelectedProviderId(providers[0]?.id ?? "");
    setSelectedLanguage(EU_LANGUAGES[0].code);
  }

  async function handleStartEncounter() {
    if (!startingFor || !selectedProviderId) return;
    setStarting(true);
    setError(null);
    try {
      const encounter = await encountersApi.startEncounter(
        startingFor.id,
        selectedProviderId,
        selectedLanguage,
      );
      navigate(`/encounters/${encounter.id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to start encounter");
    } finally {
      setStarting(false);
    }
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
                <td>
                  <button
                    className="btn"
                    disabled={providers.length === 0}
                    onClick={() => openStartEncounter(p)}
                    title={providers.length === 0 ? "No provider available to record for" : undefined}
                  >
                    Start encounter
                  </button>
                </td>
              </tr>
            ))}
            {patients.length === 0 && (
              <tr>
                <td colSpan={4} style={{ color: "var(--color-text-muted)" }}>
                  No patients yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {startingFor && (
        <Modal
          title={`Start encounter for ${startingFor.first_name} ${startingFor.last_name}`}
          onClose={() => setStartingFor(null)}
        >
          <label className="stack" style={{ gap: 4 }}>
            <span style={{ fontSize: 13, color: "var(--color-text-muted)" }}>Provider</span>
            <select
              className="input"
              value={selectedProviderId}
              onChange={(e) => setSelectedProviderId(e.target.value)}
            >
              {providers.map((prov) => (
                <option key={prov.id} value={prov.id}>
                  {prov.full_name}
                </option>
              ))}
            </select>
          </label>

          <label className="stack" style={{ gap: 4 }}>
            <span style={{ fontSize: 13, color: "var(--color-text-muted)" }}>
              Language for this visit
            </span>
            <select
              className="input"
              value={selectedLanguage}
              onChange={(e) => setSelectedLanguage(e.target.value)}
            >
              {EU_LANGUAGES.map((lang) => (
                <option key={lang.code} value={lang.code}>
                  {lang.label}
                </option>
              ))}
            </select>
          </label>

          <div className="row" style={{ justifyContent: "flex-end" }}>
            <button className="btn" onClick={() => setStartingFor(null)}>
              Cancel
            </button>
            <button
              className="btn btn-primary"
              disabled={!selectedProviderId || starting}
              onClick={handleStartEncounter}
            >
              {starting ? "Starting…" : "Start Encounter"}
            </button>
          </div>
        </Modal>
      )}
    </div>
  );
}
