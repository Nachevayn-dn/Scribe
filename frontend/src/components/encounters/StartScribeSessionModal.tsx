import { useState } from "react";
import * as encountersApi from "../../api/encounters";
import { ApiError } from "../../api/client";
import { EU_LANGUAGES } from "../../data/languages";
import type { Encounter, Patient, User } from "../../types";
import { Modal } from "../common/Modal";

interface Props {
  patient: Patient;
  providers: User[];
  onClose: () => void;
  onStarted: (encounter: Encounter) => void;
}

/** Shared by PatientListPage and DashboardPage — pass `key={patient.id}` at
 * the call site so each open gets fresh state. */
export function StartScribeSessionModal({ patient, providers, onClose, onStarted }: Props) {
  const [selectedProviderId, setSelectedProviderId] = useState(providers[0]?.id ?? "");
  const [selectedLanguage, setSelectedLanguage] = useState(EU_LANGUAGES[0].code);
  const [isScheduled, setIsScheduled] = useState(false);
  const [appointmentTime, setAppointmentTime] = useState("");
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleStart() {
    if (!selectedProviderId) return;
    setStarting(true);
    setError(null);
    try {
      const encounter = await encountersApi.startEncounter(
        patient.id,
        selectedProviderId,
        selectedLanguage,
        {
          isScheduledAppointment: isScheduled,
          appointmentTime:
            isScheduled && appointmentTime ? new Date(appointmentTime).toISOString() : undefined,
        },
      );
      onStarted(encounter);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to start Scribe session");
    } finally {
      setStarting(false);
    }
  }

  return (
    <Modal title={`Start Scribe session for ${patient.first_name} ${patient.last_name}`} onClose={onClose}>
      <label className="stack" style={{ gap: 4 }}>
        <span style={{ fontSize: 13, color: "var(--color-text-muted)" }}>Doctor</span>
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
        <span style={{ fontSize: 13, color: "var(--color-text-muted)" }}>Language for this visit</span>
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

      <label className="row" style={{ gap: 8, fontSize: 14 }}>
        <input
          type="checkbox"
          checked={isScheduled}
          onChange={(e) => setIsScheduled(e.target.checked)}
        />
        This is for a scheduled appointment
      </label>

      {isScheduled && (
        <label className="stack" style={{ gap: 4 }}>
          <span style={{ fontSize: 13, color: "var(--color-text-muted)" }}>
            Appointment date &amp; time (optional)
          </span>
          <input
            className="input"
            type="datetime-local"
            value={appointmentTime}
            onChange={(e) => setAppointmentTime(e.target.value)}
          />
        </label>
      )}

      {error && <div className="error-text">{error}</div>}

      <div className="row" style={{ justifyContent: "flex-end" }}>
        <button className="btn" onClick={onClose}>
          Cancel
        </button>
        <button
          className="btn btn-primary"
          disabled={!selectedProviderId || starting}
          onClick={handleStart}
        >
          {starting ? "Starting…" : "Start Scribe Session"}
        </button>
      </div>
    </Modal>
  );
}
