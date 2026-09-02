import { useState } from "react";
import type { NoteEntity } from "../../types";
import { EntityHighlightedLine } from "./EntityHighlightedLine";

interface Props {
  lineIndex: number;
  text: string;
  entities: NoteEntity[];
  readOnly: boolean;
  onSave: (lineIndex: number, newText: string) => Promise<void>;
}

export function NoteLineEditor({ lineIndex, text, entities, readOnly, onSave }: Props) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(text);
  const [saving, setSaving] = useState(false);

  async function commit() {
    setSaving(true);
    try {
      if (draft !== text) {
        await onSave(lineIndex, draft);
      }
      setEditing(false);
    } finally {
      setSaving(false);
    }
  }

  if (editing) {
    return (
      <textarea
        className="input"
        autoFocus
        value={draft}
        rows={Math.max(1, Math.ceil(draft.length / 80))}
        onChange={(e) => setDraft(e.target.value)}
        onBlur={commit}
        onKeyDown={(e) => {
          if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            commit();
          }
          if (e.key === "Escape") {
            setDraft(text);
            setEditing(false);
          }
        }}
        disabled={saving}
        style={{ fontFamily: "inherit", fontSize: 14 }}
      />
    );
  }

  return (
    <div
      onClick={() => !readOnly && setEditing(true)}
      style={{
        padding: "4px 6px",
        borderRadius: 4,
        cursor: readOnly ? "default" : "text",
        lineHeight: 1.6,
        minHeight: 24,
      }}
      onMouseEnter={(e) => {
        if (!readOnly) e.currentTarget.style.background = "var(--color-surface-hover)";
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.background = "transparent";
      }}
      title={readOnly ? undefined : "Click to edit this line"}
    >
      <EntityHighlightedLine text={text} entities={entities} />
    </div>
  );
}
