import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import * as dashboardApi from "../api/dashboard";
import * as patientsApi from "../api/patients";
import * as usersApi from "../api/users";
import { FirstLoginLanguageModal } from "../components/common/FirstLoginLanguageModal";
import { DateTimeWidget } from "../components/dashboard/DateTimeWidget";
import { StatWidget } from "../components/dashboard/StatWidget";
import { StartScribeSessionModal } from "../components/encounters/StartScribeSessionModal";
import { ApiError } from "../api/client";
import type { DashboardSummary, Encounter, Patient, User } from "../types";

export function DashboardPage() {
  const navigate = useNavigate();
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [patients, setPatients] = useState<Patient[]>([]);
  const [providers, setProviders] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [startingFor, setStartingFor] = useState<Patient | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const [s, p, prov] = await Promise.all([
          dashboardApi.getDashboardSummary(),
          patientsApi.listPatients(),
          usersApi.myAssignedProviders(),
        ]);
        setSummary(s);
        setPatients(p);
        setProviders(prov);
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "Failed to load dashboard");
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  function handleStarted(encounter: Encounter) {
    navigate(`/encounters/${encounter.id}`);
  }

  if (loading) return <div className="page">Loading…</div>;

  return (
    <div className="page stack">
      <FirstLoginLanguageModal />
      {error && <div className="error-text">{error}</div>}

      <div className="row" style={{ flexWrap: "wrap", alignItems: "stretch" }}>
        <DateTimeWidget />
        <StatWidget
          label="Scribe sessions this week"
          value={summary?.sessions_this_week ?? 0}
          hint="Last 7 days"
          to="/sessions?range=week"
        />
        <StatWidget
          label="Scheduled appointments"
          value={summary?.upcoming_appointments ?? 0}
          hint="Upcoming, next 7 days"
          to="/appointments?range=week"
        />
      </div>

      <div className="row" style={{ justifyContent: "space-between" }}>
        <h1 style={{ fontSize: 22 }}>Patients</h1>
        <Link className="btn" to="/patients">
          Manage patients
        </Link>
      </div>

      <div className="card">
        <table>
          <thead>
            <tr>
              <th>Name</th>
              <th>Phone</th>
              <th>Email</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {patients.map((p) => (
              <tr key={p.id}>
                <td>
                  <Link to={`/sessions?patient_id=${p.id}`}>
                    {p.first_name} {p.last_name}
                  </Link>
                </td>
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
                <td colSpan={4} style={{ color: "var(--color-text-muted)" }}>
                  No patients yet — add one from the Patients page.
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
