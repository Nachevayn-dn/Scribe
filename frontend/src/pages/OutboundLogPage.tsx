import { Fragment, useEffect, useState } from "react";
import * as outboundMessagesApi from "../api/outboundMessages";
import * as patientsApi from "../api/patients";
import { ApiError } from "../api/client";
import type { OutboundMessageLog, Patient } from "../types";

const MESSAGE_TYPE_LABELS: Record<OutboundMessageLog["message_type"], string> = {
  APPOINTMENT_CONFIRMATION: "Appointment confirmation",
  REMINDER_DAY_BEFORE: "Day-before reminder",
  REMINDER_HOURS_BEFORE: "Hours-before reminder",
};

const CHANNEL_LABELS: Record<OutboundMessageLog["channel"], string> = {
  EMAIL: "Email",
  SMS: "SMS",
  WHATSAPP: "WhatsApp",
};

/** Read-only audit log of everything the outbound agent has sent — the
 * confirmation it fires when a doctor approves a proposed appointment, and
 * its scheduled pre-procedure check-ins. */
export function OutboundLogPage() {
  const [messages, setMessages] = useState<OutboundMessageLog[]>([]);
  const [patientsById, setPatientsById] = useState<Record<string, Patient>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const [msgs, patients] = await Promise.all([
          outboundMessagesApi.listOutboundMessages(),
          patientsApi.listPatients(),
        ]);
        setMessages(msgs);
        setPatientsById(Object.fromEntries(patients.map((p) => [p.id, p])));
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "Failed to load outbound messages");
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  if (loading) return <div className="page">Loading…</div>;

  return (
    <div className="page stack">
      <h1 style={{ fontSize: 22 }}>Outbound agent</h1>
      <p style={{ margin: 0, color: "var(--color-text-muted)", fontSize: 13 }}>
        Confirmations and pre-procedure reminders the outbound agent has sent, most recent first.
      </p>

      {error && <div className="error-text">{error}</div>}

      <div className="card">
        <table>
          <thead>
            <tr>
              <th>Patient</th>
              <th>Message</th>
              <th>Channel</th>
              <th>Sent</th>
              <th>Status</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {messages.map((m) => {
              const patient = patientsById[m.patient_id];
              const isExpanded = expandedId === m.id;
              return (
                <Fragment key={m.id}>
                  <tr>
                    <td>{patient ? `${patient.first_name} ${patient.last_name}` : "—"}</td>
                    <td>{MESSAGE_TYPE_LABELS[m.message_type]}</td>
                    <td>{CHANNEL_LABELS[m.channel]}</td>
                    <td>{new Date(m.sent_at).toLocaleString()}</td>
                    <td>
                      <span style={{ color: m.status === "SENT" ? "var(--color-primary)" : "#c0392b", fontWeight: 600 }}>
                        {m.status === "SENT" ? "Sent" : "Failed"}
                      </span>
                    </td>
                    <td>
                      <button className="btn" onClick={() => setExpandedId(isExpanded ? null : m.id)}>
                        {isExpanded ? "Hide" : "View"}
                      </button>
                    </td>
                  </tr>
                  {isExpanded && (
                    <tr key={`${m.id}-detail`}>
                      <td colSpan={6}>
                        <div className="stack" style={{ gap: 4, padding: "4px 0 12px" }}>
                          <p style={{ margin: 0, whiteSpace: "pre-wrap" }}>{m.body_text}</p>
                          {m.error_message && (
                            <p style={{ margin: 0, fontSize: 13, color: "#c0392b" }}>{m.error_message}</p>
                          )}
                        </div>
                      </td>
                    </tr>
                  )}
                </Fragment>
              );
            })}
            {messages.length === 0 && (
              <tr>
                <td colSpan={6} style={{ color: "var(--color-text-muted)" }}>
                  No outbound messages yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
