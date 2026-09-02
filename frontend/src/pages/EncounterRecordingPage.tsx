import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import * as encountersApi from "../api/encounters";
import * as notesApi from "../api/notes";
import * as templatesApi from "../api/templates";
import { useAuth } from "../auth/AuthContext";
import { AudioRecorder } from "../components/audio/AudioRecorder";
import { AudioUploadStatus } from "../components/audio/AudioUploadStatus";
import { TranscriptViewer } from "../components/notes/TranscriptViewer";
import { ApiError } from "../api/client";
import type { ClinicalNote, Encounter, NoteTemplate, Transcript } from "../types";
import { NoteEditorPage } from "./NoteEditorPage";

const POLL_INTERVAL_MS = 3000;

export function EncounterRecordingPage() {
  const { encounterId } = useParams<{ encounterId: string }>();
  const { user } = useAuth();
  const navigate = useNavigate();
  const [encounter, setEncounter] = useState<Encounter | null>(null);
  const [transcript, setTranscript] = useState<Transcript | null>(null);
  const [note, setNote] = useState<ClinicalNote | null>(null);
  const [templates, setTemplates] = useState<NoteTemplate[]>([]);
  const [uploading, setUploading] = useState(false);
  const [generating, setGenerating] = useState<string | null>(null); // template_id being generated
  const [error, setError] = useState<string | null>(null);
  const pollRef = useRef<number | null>(null);

  useEffect(() => {
    templatesApi.listTemplates().then(setTemplates).catch(() => setTemplates([]));
  }, []);

  const loadEncounter = useCallback(async () => {
    if (!encounterId) return;
    const e = await encountersApi.getEncounter(encounterId);
    setEncounter(e);

    const transcriptAvailable =
      e.status === "TRANSCRIPT_READY" || e.status === "NOTE_READY" || e.status === "SIGNED";
    if (transcriptAvailable) {
      try {
        setTranscript(await notesApi.getTranscript(encounterId));
      } catch {
        // briefly not persisted yet
      }
    }
    if (e.status === "NOTE_READY" || e.status === "SIGNED") {
      try {
        setNote(await notesApi.getNote(encounterId));
      } catch {
        // briefly not persisted yet
      }
    }
    return e;
  }, [encounterId]);

  useEffect(() => {
    loadEncounter();
  }, [loadEncounter]);

  useEffect(() => {
    if (!encounter) return;
    if (encounter.status === "TRANSCRIBING") {
      pollRef.current = window.setInterval(loadEncounter, POLL_INTERVAL_MS);
      return () => {
        if (pollRef.current) window.clearInterval(pollRef.current);
      };
    }
    if (pollRef.current) window.clearInterval(pollRef.current);
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

  async function handleGenerate(templateId: string) {
    if (!encounterId) return;
    setGenerating(templateId);
    setError(null);
    try {
      const generatedNote = await notesApi.generateNote(encounterId, templateId);
      setNote(generatedNote);
      await loadEncounter(); // picks up encounter.status -> NOTE_READY
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to generate note");
    } finally {
      setGenerating(null);
    }
  }

  if (!encounter) return <div className="page">Loading…</div>;

  const canEdit =
    user?.role === "SUPER_ADMIN" || user?.role === "PROVIDER" || user?.role === "ASSISTANT";
  const canSign = user?.role === "PROVIDER" && user.id === encounter.provider_id;
  const canGenerate = canEdit; // same roles that can start/edit an encounter

  const clinicalSummary = templates.find((t) => t.template_type === "CLINICAL_SUMMARY");
  const referralLetter = templates.find((t) => t.template_type === "REFERRAL_LETTER");

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

      {transcript && (
        <div className="card stack">
          <strong>Transcript</strong>
          <div style={{ maxHeight: 320, overflowY: "auto" }}>
            <TranscriptViewer text={transcript.raw_text} />
          </div>

          {encounter.status === "TRANSCRIPT_READY" && canGenerate && (
            <div className="stack" style={{ borderTop: "1px solid var(--color-border)", paddingTop: 12 }}>
              <span style={{ fontSize: 13, color: "var(--color-text-muted)" }}>
                Recording's done — generate whichever the visit needs:
              </span>
              <div className="row">
                <button
                  className="btn btn-primary"
                  disabled={!clinicalSummary || generating !== null}
                  onClick={() => clinicalSummary && handleGenerate(clinicalSummary.id)}
                >
                  {generating === clinicalSummary?.id ? "Generating…" : "Generate Clinical Summary"}
                </button>
                <button
                  className="btn btn-primary"
                  disabled={!referralLetter || generating !== null}
                  onClick={() => referralLetter && handleGenerate(referralLetter.id)}
                >
                  {generating === referralLetter?.id ? "Generating…" : "Generate Referral Letter"}
                </button>
              </div>
            </div>
          )}
        </div>
      )}

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
