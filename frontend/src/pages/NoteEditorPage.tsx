import { useState } from "react";
import * as notesApi from "../api/notes";
import type { ClinicalNote } from "../types";
import { EntityLegend } from "../components/notes/EntityLegend";
import { NoteLineEditor } from "../components/notes/NoteLineEditor";
import { TemplateSelectorPanel } from "../components/notes/TemplateSelectorPanel";
import { ApiError } from "../api/client";

interface Props {
  encounterId: string;
  note: ClinicalNote;
  canEdit: boolean;
  canSign: boolean;
  onNoteChange: (note: ClinicalNote) => void;
}

export function NoteEditorPage({ encounterId, note, canEdit, canSign, onNoteChange }: Props) {
  const [error, setError] = useState<string | null>(null);
  const [signing, setSigning] = useState(false);
  const [switchingTemplate, setSwitchingTemplate] = useState(false);

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

      {canSign && note.status !== "SIGNED" && (
        <div>
          <button className="btn btn-primary" onClick={handleSign} disabled={signing}>
            {signing ? "Signing…" : "Sign note"}
          </button>
        </div>
      )}
    </div>
  );
}
