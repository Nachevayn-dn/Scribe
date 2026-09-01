import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import * as encountersApi from "../api/encounters";
import * as notesApi from "../api/notes";
import { useAuth } from "../auth/AuthContext";
import { AudioRecorder } from "../components/audio/AudioRecorder";
import { AudioUploadStatus } from "../components/audio/AudioUploadStatus";
import { ApiError } from "../api/client";
import type { ClinicalNote, Encounter } from "../types";
import { NoteEditorPage } from "./NoteEditorPage";

const POLL_INTERVAL_MS = 3000;

export function EncounterRecordingPage() {
  const { encounterId } = useParams<{ encounterId: string }>();
  const { user } = useAuth();
  const navigate = useNavigate();
  const [encounter, setEncounter] = useState<Encounter | null>(null);
  const [note, setNote] = useState<ClinicalNote | null>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const pollRef = useRef<number | null>(null);

  const loadEncounter = useCallback(async () => {
    if (!encounterId) return;
    const e = await encountersApi.getEncounter(encounterId);
    setEncounter(e);
    if (e.status === "NOTE_READY" || e.status === "SIGNED") {
      try {
        const n = await notesApi.getNote(encounterId);
        setNote(n);
      } catch {
        // note briefly not persisted yet; next poll will pick it up
      }
    }
    return e;
  }, [encounterId]);

  useEffect(() => {
    loadEncounter();
  }, [loadEncounter]);

  useEffect(() => {
    if (!encounter) return;
    const busy = encounter.status === "IN_PROGRESS" || encounter.status === "TRANSCRIBING" || encounter.status === "EXTRACTING";
    if (!busy) {
      if (pollRef.current) window.clearInterval(pollRef.current);
      return;
    }
    if (encounter.status === "TRANSCRIBING" || encounter.status === "EXTRACTING") {
      pollRef.current = window.setInterval(loadEncounter, POLL_INTERVAL_MS);
      return () => {
        if (pollRef.current) window.clearInterval(pollRef.current);
      };
    }
  }, [encounter, loadEncounter]);

  async function handleRecordingReady(blob: Blob, filename: string) {
    if (!encounterId) return;
    setUploading(true);
    setError(null);
    try {
      const updated = await encountersApi.uploadAudio(encounterId, blob, filename);
      setEncounter(updated);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to upload audio");
    } finally {
      setUploading(false);
    }
  }

  if (!encounter) return <div className="page">Loading…</div>;

  const canEdit =
    user?.role === "SUPER_ADMIN" || user?.role === "PROVIDER" || user?.role === "ASSISTANT";
  const canSign = user?.role === "PROVIDER" && user.id === encounter.provider_id;

  return (
    <div className="page stack">
      <button className="btn" onClick={() => navigate("/patients")} style={{ alignSelf: "flex-start" }}>
        ← Back to patients
      </button>
      <h1 style={{ fontSize: 22 }}>Encounter</h1>

      <div className="card stack">
        <AudioUploadStatus status={encounter.status} failureReason={encounter.failure_reason} />
        {error && <div className="error-text">{error}</div>}
        {encounter.status === "IN_PROGRESS" && (
          <AudioRecorder disabled={uploading} onRecordingReady={handleRecordingReady} />
        )}
      </div>

      {note && (
        <NoteEditorPage
          encounterId={encounter.id}
          note={note}
          canEdit={canEdit}
          canSign={canSign}
          onNoteChange={setNote}
        />
      )}
    </div>
  );
}
