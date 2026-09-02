import { useState } from "react";
import type { NoteEntity } from "../../types";
import { EntityHighlightedLine } from "./EntityHighlightedLine";

/** Splits a transcript into sentence-like lines for a readable "script" view.
 * Whisper doesn't return speaker labels, so this is unattributed — each line
 * is just a slice of the conversation, not "Doctor:"/"Patient:". Mirrors
 * backend/app/services/text_lines.py's regex exactly, since raw_text is
 * already persisted "\n"-joined by that same split — keep the two in sync. */
function splitIntoLines(text: string): string[] {
  return text
    .split(/(?<=[.!?])\s+(?=[A-Z0-9"'])/)
    .map((line) => line.trim())
    .filter(Boolean);
}

interface LineRowProps {
  lineIndex: number;
  text: string;
  entities: NoteEntity[];
  readOnly: boolean;
  onSave?: (lineIndex: number, newText: string) => Promise<void>;
}

/** One transcript line, with a trailing "Edit" button rather than the
 * click-anywhere-to-edit pattern NoteLineEditor uses — a script the doctor
 * is reading through benefits from a more deliberate, harder-to-fat-finger
 * entry into edit mode. */
function TranscriptLineRow({ lineIndex, text, entities, readOnly, onSave }: LineRowProps) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(text);
  const [saving, setSaving] = useState(false);

  async function commit() {
    setSaving(true);
    try {
      if (draft !== text && onSave) {
        await onSave(lineIndex, draft);
      }
      setEditing(false);
    } finally {
      setSaving(false);
    }
  }

  function cancel() {
    setDraft(text);
    setEditing(false);
  }

  return (
    <div className="row" style={{ alignItems: "flex-start", gap: 10, fontSize: 14, lineHeight: 1.6 }}>
      <span
        style={{
          color: "var(--color-text-muted)",
          fontVariantNumeric: "tabular-nums",
          minWidth: 22,
          paddingTop: 4,
        }}
      >
        {lineIndex + 1}
      </span>
      <div style={{ flex: 1, minWidth: 0 }}>
        {editing ? (
          <textarea
            className="input"
            autoFocus
            value={draft}
            rows={Math.max(1, Math.ceil(draft.length / 80))}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                commit();
              }
              if (e.key === "Escape") cancel();
            }}
            disabled={saving}
            style={{ fontFamily: "inherit", fontSize: 14, width: "100%" }}
          />
        ) : (
          <EntityHighlightedLine text={text} entities={entities} />
        )}
      </div>
      {!readOnly && onSave && !editing && (
        <button
          className="btn"
          onClick={() => {
            setDraft(text);
            setEditing(true);
          }}
          style={{ flexShrink: 0, padding: "2px 10px", fontSize: 12 }}
        >
          Edit
        </button>
      )}
      {!readOnly && onSave && editing && (
        <span className="row" style={{ gap: 4, flexShrink: 0 }}>
          <button className="btn btn-primary" disabled={saving} onClick={commit} style={{ padding: "2px 10px", fontSize: 12 }}>
            {saving ? "Saving…" : "Save"}
          </button>
          <button className="btn" disabled={saving} onClick={cancel} style={{ padding: "2px 10px", fontSize: 12 }}>
            Cancel
          </button>
        </span>
      )}
    </div>
  );
}

interface Props {
  text: string;
  entities?: NoteEntity[];
  readOnly?: boolean;
  onLineSave?: (lineIndex: number, newText: string) => Promise<void>;
}

export function TranscriptViewer({ text, entities = [], readOnly = true, onLineSave }: Props) {
  const lines = splitIntoLines(text);

  const entitiesByLine = new Map<number, NoteEntity[]>();
  for (const entity of entities) {
    const list = entitiesByLine.get(entity.line_index);
    if (list) list.push(entity);
    else entitiesByLine.set(entity.line_index, [entity]);
  }

  return (
    <div className="stack" style={{ gap: 4 }}>
      {lines.map((line, idx) => (
        <TranscriptLineRow
          key={idx}
          lineIndex={idx}
          text={line}
          entities={entitiesByLine.get(idx) ?? []}
          readOnly={readOnly}
          onSave={onLineSave}
        />
      ))}
    </div>
  );
}
