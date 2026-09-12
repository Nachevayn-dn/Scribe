import { useState } from "react";
import { useAuth } from "../../auth/AuthContext";
import { ApiError } from "../../api/client";
import * as encountersApi from "../../api/encounters";
import { EU_LANGUAGES } from "../../data/languages";
import type { Encounter, Patient, User } from "../../types";
import { StartScribeSessionModal } from "./StartScribeSessionModal";

interface Props {
  patient: Patient;
  providers: User[];
  onStarted: (encounter: Encounter) => void;
  onError?: (message: string) => void;
}

/** The "Start Scribe session" action shared by PatientListPage and
 * DashboardPage. When there's only one provider to record for — the
 * common case, a doctor starting their own session — this skips the
 * doctor/language picker modal entirely and starts immediately with
 * sensible defaults (the doctor's own language preference, not a
 * scheduled appointment). The modal only appears when there's a real
 * choice to make: an assistant supporting several doctors, or a clinic
 * admin starting a session on someone else's behalf. */
export function StartSessionButton({ patient, providers, onStarted, onError }: Props) {
  const { user } = useAuth();
  const [starting, setStarting] = useState(false);
  const [showModal, setShowModal] = useState(false);

  async function handleClick() {
    if (providers.length !== 1) {
      setShowModal(true);
      return;
    }
    setStarting(true);
    try {
      const defaultLanguage = user?.language_preference || EU_LANGUAGES[0].code;
      const encounter = await encountersApi.startEncounter(patient.id, providers[0].id, defaultLanguage);
      onStarted(encounter);
    } catch (err) {
      onError?.(err instanceof ApiError ? err.message : "Failed to start Scribe session");
    } finally {
      setStarting(false);
    }
  }

  return (
    <>
      <button
        className="btn"
        disabled={providers.length === 0 || starting}
        onClick={handleClick}
        title={providers.length === 0 ? "No doctor available to record for" : undefined}
      >
        {starting ? "Starting…" : "Start Scribe session"}
      </button>
      {showModal && (
        <StartScribeSessionModal
          patient={patient}
          providers={providers}
          onClose={() => setShowModal(false)}
          onStarted={onStarted}
        />
      )}
    </>
  );
}
