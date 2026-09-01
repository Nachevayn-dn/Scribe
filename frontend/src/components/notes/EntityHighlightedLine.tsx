import { ENTITY_COLORS } from "../../styles/entityColors";
import type { NoteEntity } from "../../types";

interface Span {
  start: number;
  end: number;
  entity: NoteEntity;
}

function resolveOffsets(text: string, entity: NoteEntity): { start: number; end: number } | null {
  // Trust start/end_offset only if the text they point at actually matches
  // the tagged entity text — extraction offsets (or a stale line edit) can
  // drift, and a mismatched slice is worse than no highlight at all.
  if (entity.start_offset !== null && entity.end_offset !== null) {
    const { start_offset: start, end_offset: end } = entity;
    if (start >= 0 && end <= text.length && start < end && text.slice(start, end) === entity.text) {
      return { start, end };
    }
  }
  // Fallback: locate the tagged text directly.
  const idx = text.indexOf(entity.text);
  if (idx >= 0) return { start: idx, end: idx + entity.text.length };
  return null;
}

export function EntityHighlightedLine({ text, entities }: { text: string; entities: NoteEntity[] }) {
  const spans: Span[] = entities
    .map((entity) => {
      const offsets = resolveOffsets(text, entity);
      return offsets ? { ...offsets, entity } : null;
    })
    .filter((s): s is Span => s !== null)
    .sort((a, b) => a.start - b.start);

  if (spans.length === 0) {
    return <span>{text || " "}</span>;
  }

  const nodes: React.ReactNode[] = [];
  let cursor = 0;
  spans.forEach((span, i) => {
    if (span.start < cursor) return; // skip overlapping spans defensively
    if (span.start > cursor) nodes.push(<span key={`plain-${i}`}>{text.slice(cursor, span.start)}</span>);
    const color = ENTITY_COLORS[span.entity.entity_type];
    nodes.push(
      <mark
        key={span.entity.id}
        title={`${color.label}${span.entity.is_edited ? " (edited)" : ""}`}
        style={{
          background: color.bg,
          border: `1px solid ${color.border}`,
          color: color.text,
          borderRadius: 4,
          padding: "0 3px",
        }}
      >
        {text.slice(span.start, span.end)}
      </mark>,
    );
    cursor = span.end;
  });
  if (cursor < text.length) nodes.push(<span key="tail">{text.slice(cursor)}</span>);

  return <>{nodes}</>;
}
