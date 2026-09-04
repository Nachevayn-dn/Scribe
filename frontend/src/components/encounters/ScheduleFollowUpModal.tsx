import { useState } from "react";
import * as appointmentsApi from "../../api/appointments";
import { ApiError } from "../../api/client";
import { googleCalendarQuickAddUrl } from "../../utils/googleCalendar";
import { Modal } from "../common/Modal";
import type { Appointment } from "../../types";

interface Props {
  patientId: string;
  providerId: string;
  patientName: string;
  providerName: string;
  sourceEncounterId?: string;
  onClose: () => void;
}

export function ScheduleFollowUpModal({
  patientId,
  providerId,
  patientName,
  providerName,
  sourceEncounterId,
  onClose,
}: Props) {
  const [date, setDate] = useState("");
  const [reason, setReason] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [booked, setBooked] = useState<Appointment | null>(null);

  async function handleSchedule() {
    if (!date) {
      setError("Pick a date and time");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const appointment = await appointmentsApi.scheduleAppointment({
        patient_id: patientId,
        provider_id: providerId,
        scheduled_time: new Date(date).toISOString(),
        reason: reason.trim() || undefined,
        source_encounter_id: sourceEncounterId,
      });
      setBooked(appointment);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to schedule follow-up");
    } finally {
      setSaving(false);
    }
  }

  const calendarUrl =
    booked &&
    googleCalendarQuickAddUrl({
      title: `Follow-up — ${patientName}`,
      start: new Date(booked.scheduled_time),
      details: `MedicDesk.ai follow-up with ${providerName}.${booked.reason ? ` ${booked.reason}` : ""}`,
    });

  return (
    <Modal title="Schedule follow-up" onClose={onClose}>
      {booked ? (
        <div className="stack">
          <p style={{ margin: 0 }}>
            Follow-up for {patientName} booked for {new Date(booked.scheduled_time).toLocaleString()}.
          </p>
          <div className="row" style={{ justifyContent: "flex-end" }}>
            {calendarUrl && (
              <a className="btn" href={calendarUrl} target="_blank" rel="noreferrer">
                Add to Google Calendar
              </a>
            )}
            <button className="btn btn-primary" onClick={onClose}>
              Done
            </button>
          </div>
        </div>
      ) : (
        <>
          <label className="stack" style={{ gap: 4 }}>
            <span style={{ fontSize: 13, color: "var(--color-text-muted)" }}>
              Follow-up date &amp; time for {patientName}
            </span>
            <input
              className="input"
              type="datetime-local"
              value={date}
              onChange={(e) => setDate(e.target.value)}
            />
          </label>

          <label className="stack" style={{ gap: 4 }}>
            <span style={{ fontSize: 13, color: "var(--color-text-muted)" }}>Reason (optional)</span>
            <input
              className="input"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="e.g. Review labs, check medication response"
            />
          </label>

          {error && <div className="error-text">{error}</div>}

          <div className="row" style={{ justifyContent: "flex-end" }}>
            <button className="btn" onClick={onClose}>
              Cancel
            </button>
            <button className="btn btn-primary" disabled={saving} onClick={handleSchedule}>
              {saving ? "Scheduling…" : "Schedule"}
            </button>
          </div>
        </>
      )}
    </Modal>
  );
}
