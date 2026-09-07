import { Fragment, useEffect, useMemo, useState } from "react";
import * as appointmentsApi from "../api/appointments";
import * as callsApi from "../api/calls";
import * as patientsApi from "../api/patients";
import * as usersApi from "../api/users";
import { ApiError } from "../api/client";
import type { Appointment, CallSession, Patient, User } from "../types";

const OUTCOME_LABELS: Record<CallSession["outcome"], string> = {
  IN_PROGRESS: "In progress",
  APPOINTMENT_PROPOSED: "Appointment proposed",
  INFO_ONLY: "Info only",
  EMERGENCY_ESCALATED: "Emergency escalated",
  ABANDONED: "Call abandoned",
};

const OUTCOME_COLORS: Record<CallSession["outcome"], string> = {
  IN_PROGRESS: "var(--color-text-muted)",
  APPOINTMENT_PROPOSED: "var(--color-primary)",
  INFO_ONLY: "var(--color-text-muted)",
  EMERGENCY_ESCALATED: "#c0392b",
  ABANDONED: "var(--color-text-muted)",
};

function formatDuration(seconds: number | null): string {
  if (seconds === null) return "—";
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${String(s).padStart(2, "0")}`;
}

/** What the inbound agent produced — every call it answered, with the
 * transcript/summary it wrote and, when it proposed an appointment, the
 * one-click approval the doctor takes to confirm it (see
 * POST /calls/{id}/approve-appointment). */
export function InboundCallsPage() {
  const [calls, setCalls] = useState<CallSession[]>([]);
  const [appointmentsById, setAppointmentsById] = useState<Record<string, Appointment>>({});
  const [patientsById, setPatientsById] = useState<Record<string, Patient>>({});
  const [providersById, setProvidersById] = useState<Record<string, User>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [approving, setApproving] = useState<string | null>(null);

  async function refresh() {
    setLoading(true);
    try {
      const [callList, appointments, patients, providers] = await Promise.all([
        callsApi.listCalls(),
        appointmentsApi.listAppointments(),
        patientsApi.listPatients(),
        usersApi.myAssignedProviders(),
      ]);
      setCalls(callList);
      setAppointmentsById(Object.fromEntries(appointments.map((a) => [a.id, a])));
      setPatientsById(Object.fromEntries(patients.map((p) => [p.id, p])));
      setProvidersById(Object.fromEntries(providers.map((p) => [p.id, p])));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load calls");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  const sorted = useMemo(
    () => [...calls].sort((a, b) => new Date(b.started_at).getTime() - new Date(a.started_at).getTime()),
    [calls],
  );

  async function handleApprove(callId: string) {
    setApproving(callId);
    try {
      await callsApi.approveAppointment(callId);
      await refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to approve appointment");
    } finally {
      setApproving(null);
    }
  }

  if (loading) return <div className="page">Loading…</div>;

  return (
    <div className="page stack">
      <div className="row" style={{ justifyContent: "space-between" }}>
        <h1 style={{ fontSize: 22 }}>Inbound agent</h1>
      </div>
      <p style={{ margin: 0, color: "var(--color-text-muted)", fontSize: 13 }}>
        Calls and WhatsApp conversations the inbound agent handled, most recent first.
      </p>

      {error && <div className="error-text">{error}</div>}

      <div className="card">
        <table>
          <thead>
            <tr>
              <th>Caller</th>
              <th>Doctor</th>
              <th>When</th>
              <th>Duration</th>
              <th>Outcome</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((call) => {
              const patient = call.patient_id ? patientsById[call.patient_id] : null;
              const provider = call.provider_id ? providersById[call.provider_id] : null;
              const appointment = call.proposed_appointment_id
                ? appointmentsById[call.proposed_appointment_id]
                : null;
              const isApproved = appointment?.status === "SCHEDULED";
              const canApprove =
                call.outcome === "APPOINTMENT_PROPOSED" && call.proposed_appointment_id && !isApproved;
              const isExpanded = expandedId === call.id;

              return (
                <Fragment key={call.id}>
                  <tr>
                    <td>
                      {patient ? `${patient.first_name} ${patient.last_name}` : call.from_number}
                    </td>
                    <td>{provider?.full_name ?? "—"}</td>
                    <td>{new Date(call.started_at).toLocaleString()}</td>
                    <td>{formatDuration(call.duration_seconds)}</td>
                    <td>
                      <span style={{ color: OUTCOME_COLORS[call.outcome], fontWeight: 600 }}>
                        {OUTCOME_LABELS[call.outcome]}
                      </span>
                    </td>
                    <td>
                      <div className="row" style={{ justifyContent: "flex-end" }}>
                        <button className="btn" onClick={() => setExpandedId(isExpanded ? null : call.id)}>
                          {isExpanded ? "Hide" : "View"}
                        </button>
                        {canApprove && (
                          <button
                            className="btn btn-primary"
                            disabled={approving === call.id}
                            onClick={() => handleApprove(call.id)}
                          >
                            {approving === call.id ? "Approving…" : "Approve appointment"}
                          </button>
                        )}
                        {isApproved && (
                          <span style={{ color: "var(--color-primary)", fontSize: 13, alignSelf: "center" }}>
                            ✓ Approved
                          </span>
                        )}
                      </div>
                    </td>
                  </tr>
                  {isExpanded && (
                    <tr key={`${call.id}-detail`}>
                      <td colSpan={6}>
                        <div className="stack" style={{ gap: 8, padding: "4px 0 12px" }}>
                          {call.summary_text && (
                            <div>
                              <strong style={{ fontSize: 13 }}>Summary</strong>
                              <p style={{ margin: "4px 0 0" }}>{call.summary_text}</p>
                            </div>
                          )}
                          {appointment && (
                            <div style={{ fontSize: 13, color: "var(--color-text-muted)" }}>
                              Proposed: {new Date(appointment.scheduled_time).toLocaleString()}
                              {appointment.reason ? ` — ${appointment.reason}` : ""}
                            </div>
                          )}
                          {call.recording_sid && (
                            <div style={{ fontSize: 13, color: "var(--color-text-muted)" }}>🎙 Call was recorded</div>
                          )}
                          <div>
                            <strong style={{ fontSize: 13 }}>Transcript</strong>
                            <pre
                              style={{
                                margin: "4px 0 0",
                                whiteSpace: "pre-wrap",
                                fontFamily: "inherit",
                                fontSize: 13,
                                color: "var(--color-text-muted)",
                                maxHeight: 240,
                                overflowY: "auto",
                              }}
                            >
                              {call.transcript_text || "No transcript recorded."}
                            </pre>
                          </div>
                        </div>
                      </td>
                    </tr>
                  )}
                </Fragment>
              );
            })}
            {sorted.length === 0 && (
              <tr>
                <td colSpan={6} style={{ color: "var(--color-text-muted)" }}>
                  No inbound calls yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
