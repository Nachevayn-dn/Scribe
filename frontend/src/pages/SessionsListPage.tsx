import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import * as encountersApi from "../api/encounters";
import * as patientsApi from "../api/patients";
import * as usersApi from "../api/users";
import { ApiError } from "../api/client";
import type { Encounter, Patient, User } from "../types";

const STATUS_LABELS: Record<string, string> = {
  IN_PROGRESS: "In progress",
  TRANSCRIBING: "Transcribing",
  TRANSCRIPT_READY: "Transcript ready",
  EXTRACTING: "Generating note",
  NOTE_READY: "Note ready",
  SIGNED: "Signed",
  FAILED: "Failed",
};

const WEEK_MS = 7 * 24 * 60 * 60 * 1000;

/** All Scribe sessions the current user can see (role-scoped server-side,
 * same as the dashboard widgets). Reachable from the "Scribe sessions this
 * week" widget (?range=week), from a patient's name (?patient_id=...), or
 * directly via the nav link. */
export function SessionsListPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const patientIdFilter = searchParams.get("patient_id");
  const range = searchParams.get("range") === "week" ? "week" : "all";

  const [encounters, setEncounters] = useState<Encounter[]>([]);
  const [patientsById, setPatientsById] = useState<Record<string, Patient>>({});
  const [providersById, setProvidersById] = useState<Record<string, User>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    (async () => {
      try {
        const [enc, patients, providers] = await Promise.all([
          encountersApi.listEncounters(patientIdFilter ? { patient_id: patientIdFilter } : undefined),
          patientsApi.listPatients(),
          usersApi.myAssignedProviders(),
        ]);
        setEncounters(enc);
        setPatientsById(Object.fromEntries(patients.map((p) => [p.id, p])));
        setProvidersById(Object.fromEntries(providers.map((p) => [p.id, p])));
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "Failed to load sessions");
      } finally {
        setLoading(false);
      }
    })();
  }, [patientIdFilter]);

  const visible = useMemo(() => {
    const sorted = [...encounters].sort(
      (a, b) => new Date(b.started_at).getTime() - new Date(a.started_at).getTime(),
    );
    if (patientIdFilter || range !== "week") return sorted;
    const cutoff = Date.now() - WEEK_MS;
    return sorted.filter((e) => new Date(e.started_at).getTime() >= cutoff);
  }, [encounters, range, patientIdFilter]);

  if (loading) return <div className="page">Loading…</div>;

  const filterPatient = patientIdFilter ? patientsById[patientIdFilter] : null;

  return (
    <div className="page stack">
      <div className="row" style={{ justifyContent: "space-between" }}>
        <h1 style={{ fontSize: 22 }}>
          {filterPatient ? `Scribe sessions for ${filterPatient.first_name} ${filterPatient.last_name}` : "Scribe sessions"}
        </h1>
        <div className="row">
          {patientIdFilter && (
            <Link className="btn" to="/sessions">
              All sessions
            </Link>
          )}
          <Link className="btn" to="/patients">
            + Start a session
          </Link>
        </div>
      </div>

      {!patientIdFilter && (
        <div className="row">
          <button
            className="btn"
            style={range === "week" ? { borderColor: "var(--color-primary)", color: "var(--color-primary)" } : undefined}
            onClick={() => setSearchParams({ range: "week" })}
          >
            This week
          </button>
          <button
            className="btn"
            style={range === "all" ? { borderColor: "var(--color-primary)", color: "var(--color-primary)" } : undefined}
            onClick={() => setSearchParams({})}
          >
            All time
          </button>
        </div>
      )}

      {error && <div className="error-text">{error}</div>}

      <div className="card">
        <table>
          <thead>
            <tr>
              {!filterPatient && <th>Patient</th>}
              <th>Doctor</th>
              <th>Started</th>
              <th>Status</th>
              <th>Scheduled?</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {visible.map((e) => {
              const patient = patientsById[e.patient_id];
              const provider = providersById[e.provider_id];
              return (
                <tr key={e.id}>
                  {!filterPatient && (
                    <td>
                      {patient ? (
                        <Link to={`/sessions?patient_id=${patient.id}`}>
                          {patient.first_name} {patient.last_name}
                        </Link>
                      ) : (
                        "—"
                      )}
                    </td>
                  )}
                  <td>{provider?.full_name ?? "—"}</td>
                  <td>{new Date(e.started_at).toLocaleString()}</td>
                  <td>
                    <span className="badge">{STATUS_LABELS[e.status] ?? e.status}</span>
                  </td>
                  <td>{e.is_scheduled_appointment ? "Yes" : "—"}</td>
                  <td>
                    <Link className="btn" to={`/encounters/${e.id}`}>
                      Open
                    </Link>
                  </td>
                </tr>
              );
            })}
            {visible.length === 0 && (
              <tr>
                <td colSpan={filterPatient ? 5 : 6} style={{ color: "var(--color-text-muted)" }}>
                  {patientIdFilter
                    ? "No sessions yet for this patient."
                    : range === "week"
                      ? "No sessions in the last 7 days."
                      : "No sessions yet."}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
