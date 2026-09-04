import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import * as appointmentsApi from "../api/appointments";
import * as patientsApi from "../api/patients";
import * as usersApi from "../api/users";
import { ApiError } from "../api/client";
import { googleCalendarQuickAddUrl } from "../utils/googleCalendar";
import type { Appointment, Patient, User } from "../types";

const WEEK_MS = 7 * 24 * 60 * 60 * 1000;

/** Upcoming follow-up appointments — booked via "Schedule follow-up" on a
 * signed note, reachable from the dashboard's "Scheduled appointments"
 * widget or from a patient's name. Distinct from the Sessions list: an
 * Appointment is a future booking with no recording yet. */
export function AppointmentsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const patientIdFilter = searchParams.get("patient_id");
  const range = searchParams.get("range") === "week" ? "week" : "all";

  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [patientsById, setPatientsById] = useState<Record<string, Patient>>({});
  const [providersById, setProvidersById] = useState<Record<string, User>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [cancelling, setCancelling] = useState<string | null>(null);

  async function refresh() {
    setLoading(true);
    try {
      const [appts, patients, providers] = await Promise.all([
        appointmentsApi.listAppointments(
          patientIdFilter ? { patient_id: patientIdFilter } : undefined,
        ),
        patientsApi.listPatients(),
        usersApi.myAssignedProviders(),
      ]);
      setAppointments(appts);
      setPatientsById(Object.fromEntries(patients.map((p) => [p.id, p])));
      setProvidersById(Object.fromEntries(providers.map((p) => [p.id, p])));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load appointments");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [patientIdFilter]);

  const visible = useMemo(() => {
    let list = [...appointments]
      .filter((a) => a.status === "SCHEDULED")
      .sort((a, b) => new Date(a.scheduled_time).getTime() - new Date(b.scheduled_time).getTime());
    if (!patientIdFilter && range === "week") {
      const cutoff = Date.now() + WEEK_MS;
      list = list.filter((a) => new Date(a.scheduled_time).getTime() <= cutoff);
    }
    return list;
  }, [appointments, range, patientIdFilter]);

  function toggleParam(key: string, value: string | null) {
    const next = new URLSearchParams(searchParams);
    if (value === null) next.delete(key);
    else next.set(key, value);
    setSearchParams(next);
  }

  async function handleCancel(appointmentId: string) {
    setCancelling(appointmentId);
    try {
      await appointmentsApi.updateAppointment(appointmentId, { status: "CANCELLED" });
      await refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to cancel appointment");
    } finally {
      setCancelling(null);
    }
  }

  if (loading) return <div className="page">Loading…</div>;

  const filterPatient = patientIdFilter ? patientsById[patientIdFilter] : null;

  return (
    <div className="page stack">
      <div className="row" style={{ justifyContent: "space-between" }}>
        <h1 style={{ fontSize: 22 }}>
          {filterPatient
            ? `Upcoming appointments for ${filterPatient.first_name} ${filterPatient.last_name}`
            : "Upcoming appointments"}
        </h1>
        <div className="row">
          {patientIdFilter && (
            <Link className="btn" to="/appointments">
              All appointments
            </Link>
          )}
          <Link className="btn" to="/sessions">
            Scribe sessions
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
            Next 7 days
          </button>
          <button
            className="btn"
            style={range === "all" ? { borderColor: "var(--color-primary)", color: "var(--color-primary)" } : undefined}
            onClick={() => toggleParam("range", null)}
          >
            All upcoming
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
              <th>When</th>
              <th>Reason</th>
              <th></th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {visible.map((a) => {
              const patient = patientsById[a.patient_id];
              const provider = providersById[a.provider_id];
              const patientName = patient ? `${patient.first_name} ${patient.last_name}` : "this patient";
              const calendarUrl = googleCalendarQuickAddUrl({
                title: `Follow-up — ${patientName}`,
                start: new Date(a.scheduled_time),
                details: `MedicDesk.ai follow-up with ${provider?.full_name ?? "your doctor"}.${
                  a.reason ? ` ${a.reason}` : ""
                }`,
              });
              return (
                <tr key={a.id}>
                  {!filterPatient && (
                    <td>
                      {patient ? (
                        <Link to={`/appointments?patient_id=${patient.id}`}>
                          {patient.first_name} {patient.last_name}
                        </Link>
                      ) : (
                        "—"
                      )}
                    </td>
                  )}
                  <td>{provider?.full_name ?? "—"}</td>
                  <td>{new Date(a.scheduled_time).toLocaleString()}</td>
                  <td>{a.reason ?? "—"}</td>
                  <td>
                    <a className="btn" href={calendarUrl} target="_blank" rel="noreferrer">
                      Add to Google Calendar
                    </a>
                  </td>
                  <td>
                    <button
                      className="btn"
                      disabled={cancelling === a.id}
                      onClick={() => handleCancel(a.id)}
                    >
                      {cancelling === a.id ? "Cancelling…" : "Cancel"}
                    </button>
                  </td>
                </tr>
              );
            })}
            {visible.length === 0 && (
              <tr>
                <td colSpan={filterPatient ? 5 : 6} style={{ color: "var(--color-text-muted)" }}>
                  {patientIdFilter
                    ? "No upcoming appointments for this patient."
                    : range === "week"
                      ? "No appointments in the next 7 days."
                      : "No upcoming appointments."}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
