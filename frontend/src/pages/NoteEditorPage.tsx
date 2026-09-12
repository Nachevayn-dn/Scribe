import { useEffect, useState } from "react";
import * as notesApi from "../api/notes";
import type { ClinicalNote, PatientShareLog } from "../types";
import { ScheduleFollowUpModal } from "../components/encounters/ScheduleFollowUpModal";
import { ShareEmailModal } from "../components/encounters/ShareEmailModal";
import { AskAIPanel } from "../components/notes/AskAIPanel";
import { EntityLegend } from "../components/notes/EntityLegend";
import { NoteLineEditor } from "../components/notes/NoteLineEditor";
import { TemplateSelectorPanel } from "../components/notes/TemplateSelectorPanel";
import { ApiError } from "../api/client";

interface Props {
  encounterId: string;
  patientId: string;
  providerId: string;
  patientName: string;
  patientEmail: string | null;
  providerName: string;
  note: ClinicalNote;
  canEdit: boolean;
  canSign: boolean;
  onNoteChange: (note: ClinicalNote) => void;
}

export function NoteEditorPage({
  encounterId,
  patientId,
  providerId,
  patientName,
  patientEmail,
  providerName,
  note,
  canEdit,
  canSign,
  onNoteChange,
}: Props) {
  const [error, setError] = useState<string | null>(null);
  const [signing, setSigning] = useState(false);
  const [switchingTemplate, setSwitchingTemplate] = useState(false);
  const [sharing, setSharing] = useState(false);
  const [scheduling, setScheduling] = useState(false);
  const [copyStatus, setCopyStatus] = useState<"idle" | "copied">("idle");
  const [sharingWithPatient, setSharingWithPatient] = useState(false);
  const [patientShares, setPatientShares] = useState<PatientShareLog[]>([]);

  useEffect(() => {
    if (note.status !== "SIGNED") return;
    notesApi.listPatientShares(encounterId).then(setPatientShares).catch(() => setPatientShares([]));
  }, [encounterId, note.status]);

  async function handleShareWithPatient() {
    if (!patientEmail) return;
    if (!window.confirm(`Send this summary to ${patientName} at ${patientEmail}?`)) return;
    setSharingWithPatient(true);
    setError(null);
    try {
      await notesApi.shareNoteWithPatient(encounterId);
      const shares = await notesApi.listPatientShares(encounterId);
      setPatientShares(shares);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to send to patient");
    } finally {
      setSharingWithPatient(false);
    }
  }

  const lines = note.rendered_content.split("\n");
  const readOnly = !canEdit || note.status === "SIGNED";

  async function handleTemplateChange(templateId: string) {
    if (templateId === note.template_id) return;
    setSwitchingTemplate(true);
    setError(null);
    try {
      const updated = await notesApi.generateNote(encounterId, templateId);
      onNoteChange(updated);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to switch template");
    } finally {
      setSwitchingTemplate(false);
    }
  }

  async function handleLineSave(lineIndex: number, newText: string) {
    try {
      const updated = await notesApi.editNoteLine(encounterId, lineIndex, newText);
      onNoteChange(updated);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to save edit");
    }
  }

  async function handleApplyRevision(revisedContent: string) {
    const updated = await notesApi.replaceNoteContent(encounterId, revisedContent);
    onNoteChange(updated);
  }

  async function handleCopyForPms() {
    try {
      await navigator.clipboard.writeText(note.rendered_content);
    } catch {
      // Clipboard permission can be denied by the browser — the custom
      // event below still fires either way, so the extension (if
      // installed) can still pick the text up and offer its own paste.
    }
    // Lets the optional MedicDesk Chrome extension's content script (see
    // /extension) grab the note text too, so its "paste into PMS" action
    // has something to paste even if the page didn't have clipboard
    // permission. No-ops harmlessly if the extension isn't installed.
    window.postMessage({ source: "medicdesk", type: "NOTE_COPIED", text: note.rendered_content }, "*");
    setCopyStatus("copied");
    setTimeout(() => setCopyStatus("idle"), 2000);
  }

  async function handleSign() {
    setSigning(true);
    setError(null);
    try {
      const updated = await notesApi.signNote(encounterId);
      onNoteChange(updated);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to sign note");
    } finally {
      setSigning(false);
    }
  }

  return (
    <div className="card stack">
      <div className="row" style={{ justifyContent: "space-between" }}>
        <div className="row">
          <strong>Clinical note</strong>
          <span
            className="badge"
            style={
              note.status === "SIGNED"
                ? { background: "rgba(74, 222, 128, 0.16)", color: "#4ade80" }
                : undefined
            }
          >
            {note.status}
          </span>
        </div>
        {canEdit && (
          <div className="row">
            <button className="btn" onClick={() => setScheduling(true)}>
              Schedule follow-up
            </button>
            <button className="btn" onClick={() => setSharing(true)}>
              Share via email
            </button>
            {note.status === "SIGNED" && (
              <button
                className="btn"
                onClick={handleShareWithPatient}
                disabled={sharingWithPatient || !patientEmail}
                title={patientEmail ? undefined : "Add an email for this patient first"}
              >
                {sharingWithPatient ? "Sending…" : "Share with patient"}
              </button>
            )}
            <button className="btn" onClick={handleCopyForPms} title="Copies the note so you can paste it into your PMS">
              {copyStatus === "copied" ? "Copied ✓" : "Copy for PMS"}
            </button>
          </div>
        )}
      </div>

      <EntityLegend />

      {canEdit && note.status !== "SIGNED" && (
        <TemplateSelectorPanel
          value={note.template_id}
          onChange={handleTemplateChange}
          disabled={switchingTemplate}
        />
      )}

      <div className="stack" style={{ gap: 2 }}>
        {lines.map((lineText, idx) => (
          <NoteLineEditor
            key={idx}
            lineIndex={idx}
            text={lineText}
            entities={note.entities.filter((e) => e.line_index === idx)}
            readOnly={readOnly}
            onSave={handleLineSave}
          />
        ))}
      </div>

      {error && <div className="error-text">{error}</div>}

      {note.status === "SIGNED" && patientShares.length > 0 && (
        <div className="stack" style={{ gap: 4, fontSize: 13, color: "var(--color-text-muted)" }}>
          <strong style={{ fontSize: 13, color: "var(--color-text)" }}>Shared with patient</strong>
          {patientShares.map((share) => (
            <div key={share.id}>
              Sent to {share.recipient_email} on {new Date(share.sent_at).toLocaleString()}
            </div>
          ))}
        </div>
      )}

      {canSign && note.status !== "SIGNED" && (
        <div>
          <button className="btn btn-primary" onClick={handleSign} disabled={signing}>
            {signing ? "Signing…" : "Sign note"}
          </button>
        </div>
      )}

      {canEdit && note.status !== "SIGNED" && (
        <AskAIPanel encounterId={encounterId} onApply={handleApplyRevision} />
      )}

      {sharing && (
        <ShareEmailModal encounterId={encounterId} contentType="note" onClose={() => setSharing(false)} />
      )}

      {scheduling && (
        <ScheduleFollowUpModal
          patientId={patientId}
          providerId={providerId}
          patientName={patientName}
          providerName={providerName}
          sourceEncounterId={encounterId}
          onClose={() => setScheduling(false)}
        />
      )}
    </div>
  );
}
