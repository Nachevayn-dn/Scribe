import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import * as dashboardApi from "../api/dashboard";
import * as patientsApi from "../api/patients";
import * as usersApi from "../api/users";
import { useAuth } from "../auth/AuthContext";
import { FirstLoginLanguageModal } from "../components/common/FirstLoginLanguageModal";
import { DateTimeWidget } from "../components/dashboard/DateTimeWidget";
import { StatWidget } from "../components/dashboard/StatWidget";
import { StartSessionButton } from "../components/encounters/StartSessionButton";
import { ApiError } from "../api/client";
import type { DashboardSummary, Encounter, Patient, User } from "../types";

/** Full names in this app are commonly "Dr. <First> <Last>" — greet with
 * just the first real name, not the title itself. Falls back sensibly for
 * a name with no title, or a single word. */
function greetingName(fullName: string | undefined): string {
  if (!fullName) return "there";
  const parts = fullName.trim().split(/\s+/);
  if (parts.length > 1 && /^dr\.?$/i.test(parts[0])) return parts[1];
  return parts[0];
}

export function DashboardPage() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [recapText, setRecapText] = useState<string | null>(null);
  const [patients, setPatients] = useState<Patient[]>([]);
  const [providers, setProviders] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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

    // Fetched separately from the rest of the dashboard, and never lets a
    // failure block the page — it's a nice-to-have sentence, not a widget
    // anyone depends on.
    dashboardApi
      .getDailyRecap()
      .then((r) => setRecapText(r.summary_text))
      .catch(() => setRecapText(null));
  }, []);

  function handleStarted(encounter: Encounter) {
    navigate(`/encounters/${encounter.id}`);
  }

  if (loading) return <div className="page">Loading…</div>;

  return (
    <div className="page stack">
      <FirstLoginLanguageModal />
      {error && <div className="error-text">{error}</div>}

      {recapText && (
        <div className="card" style={{ background: "var(--color-surface-alt, var(--color-surface))" }}>
          <p style={{ margin: 0 }}>
            👋 Hi {greetingName(user?.full_name)} — {recapText}
          </p>
        </div>
      )}

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
        <StatWidget
          label="Inbound calls"
          value={summary?.inbound_calls_this_week ?? 0}
          hint="Last 7 days"
          to="/clinic/inbound"
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
                  <StartSessionButton patient={p} providers={providers} onStarted={handleStarted} onError={setError} />
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
    </div>
  );
}
