import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import * as encountersApi from "../api/encounters";
import * as patientsApi from "../api/patients";
import * as usersApi from "../api/users";
import { ApiError } from "../api/client";
import { googleCalendarQuickAddUrl } from "../utils/googleCalendar";
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

/** Returns null when there's no appointment_time to anchor the event to. */
function googleCalendarUrl(encounter: Encounter, patientName: string, providerName: string): string | null {
  if (!encounter.appointment_time) return null;
  return googleCalendarQuickAddUrl({
    title: `Scribe session — ${patientName}`,
    start: new Date(encounter.appointment_time),
    details: `MedicDesk.ai Scribe session with ${providerName}.`,
  });
}

/** All Scribe sessions the current user can see (role-scoped server-side,
 * same as the dashboard widgets). Reachable from a dashboard widget
 * (?range=week, optionally &scheduled=true), from a patient's name
 * (?patient_id=...), or directly via the nav link. */
export function SessionsListPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const patientIdFilter = searchParams.get("patient_id");
  const range = searchParams.get("range") === "week" ? "week" : "all";
  const scheduledOnly = searchParams.get("scheduled") === "true";

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
    let list = [...encounters].sort(
      (a, b) => new Date(b.started_at).getTime() - new Date(a.started_at).getTime(),
    );
    if (scheduledOnly) list = list.filter((e) => e.is_scheduled_appointment);
    if (!patientIdFilter && range === "week") {
      const cutoff = Date.now() - WEEK_MS;
      list = list.filter((e) => new Date(e.started_at).getTime() >= cutoff);
    }
    return list;
  }, [encounters, range, patientIdFilter, scheduledOnly]);

  function toggleParam(key: string, value: string | null) {
    const next = new URLSearchParams(searchParams);
    if (value === null) next.delete(key);
    else next.set(key, value);
    setSearchParams(next);
  }

  if (loading) return <div className="page">Loading…</div>;

  const filterPatient = patientIdFilter ? patientsById[patientIdFilter] : null;

  return (
    <div className="page stack">
      <div className="row" style={{ justifyContent: "space-between" }}>
        <h1 style={{ fontSize: 22 }}>
          {filterPatient
            ? `Scribe sessions for ${filterPatient.first_name} ${filterPatient.last_name}`
            : scheduledOnly
              ? "Scheduled appointments"
              : "Scribe sessions"}
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
        <div className="row" style={{ flexWrap: "wrap" }}>
          <button
            className="btn"
            style={range === "week" ? { borderColor: "var(--color-primary)", color: "var(--color-primary)" } : undefined}
            onClick={() => toggleParam("range", "week")}
          >
            This week
          </button>
          <button
            className="btn"
            style={range === "all" ? { borderColor: "var(--color-primary)", color: "var(--color-primary)" } : undefined}
            onClick={() => toggleParam("range", null)}
          >
            All time
          </button>
          <span style={{ width: 1, background: "var(--color-border)", alignSelf: "stretch" }} />
          <button
            className="btn"
            style={scheduledOnly ? { borderColor: "var(--color-primary)", color: "var(--color-primary)" } : undefined}
            onClick={() => toggleParam("scheduled", scheduledOnly ? null : "true")}
          >
            {scheduledOnly ? "✓ Scheduled only" : "Scheduled only"}
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
              <th></th>
            </tr>
          </thead>
          <tbody>
            {visible.map((e) => {
              const patient = patientsById[e.patient_id];
              const provider = providersById[e.provider_id];
              const patientName = patient ? `${patient.first_name} ${patient.last_name}` : "this patient";
              const calendarUrl = e.is_scheduled_appointment
                ? googleCalendarUrl(e, patientName, provider?.full_name ?? "your doctor")
                : null;
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
                  <td>
                    {e.is_scheduled_appointment && e.appointment_time
                      ? new Date(e.appointment_time).toLocaleString()
                      : new Date(e.started_at).toLocaleString()}
                  </td>
                  <td>
                    <span className="badge">{STATUS_LABELS[e.status] ?? e.status}</span>
                  </td>
                  <td>{e.is_scheduled_appointment ? "Yes" : "—"}</td>
                  <td>
                    {e.is_scheduled_appointment &&
                      (calendarUrl ? (
                        <a className="btn" href={calendarUrl} target="_blank" rel="noreferrer">
                          Add to Google Calendar
                        </a>
                      ) : (
                        <span style={{ fontSize: 12, color: "var(--color-text-muted)" }} title="No date/time was set when this session was started">
                          No time set
                        </span>
                      ))}
                  </td>
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
                <td colSpan={filterPatient ? 6 : 7} style={{ color: "var(--color-text-muted)" }}>
                  {scheduledOnly
                    ? "No scheduled appointments in this range."
                    : patientIdFilter
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
