import { useState } from "react";
import * as notesApi from "../api/notes";
import type { ClinicalNote } from "../types";
import { EntityLegend } from "../components/notes/EntityLegend";
import { NoteLineEditor } from "../components/notes/NoteLineEditor";
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

  const lines = note.rendered_content.split("\n");
  const readOnly = !canEdit || note.status === "SIGNED";

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
        <span className="badge" style={{ background: note.status === "SIGNED" ? "#dcfce7" : "#eef2ff", color: note.status === "SIGNED" ? "#166534" : "#3730a3" }}>
          {note.status}
        </span>
      </div>

      <EntityLegend />

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
