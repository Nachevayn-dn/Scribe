/** Splits a transcript into sentence-like lines for a readable "script" view.
 * Whisper doesn't return speaker labels, so this is unattributed — each line
 * is just a slice of the conversation, not "Doctor:"/"Patient:". */
function splitIntoLines(text: string): string[] {
  return text
    .split(/(?<=[.!?])\s+(?=[A-Z0-9"'])/)
    .map((line) => line.trim())
    .filter(Boolean);
}

export function TranscriptViewer({ text }: { text: string }) {
  const lines = splitIntoLines(text);

  return (
    <div className="stack" style={{ gap: 4 }}>
      {lines.map((line, idx) => (
        <div
          key={idx}
          className="row"
          style={{ alignItems: "flex-start", gap: 10, fontSize: 14, lineHeight: 1.6 }}
        >
          <span style={{ color: "var(--color-text-muted)", fontVariantNumeric: "tabular-nums", minWidth: 22 }}>
            {idx + 1}
          </span>
          <span>{line}</span>
        </div>
      ))}
    </div>
  );
}
