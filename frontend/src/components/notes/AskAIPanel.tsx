import { useState } from "react";
import * as notesApi from "../../api/notes";
import { ApiError } from "../../api/client";
import type { AskAIResult } from "../../types";

interface Props {
  encounterId: string;
  onApply: (revisedContent: string) => Promise<void>;
}

/** Free-form instruction against the note. Claude decides whether it's a
 * rework (shows a proposed replacement the doctor must explicitly Apply —
 * never auto-saved) or a lookup (shows an answer with sources, purely
 * informational, never touches the note). */
export function AskAIPanel({ encounterId, onApply }: Props) {
  const [instruction, setInstruction] = useState("");
  const [asking, setAsking] = useState(false);
  const [applying, setApplying] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<AskAIResult | null>(null);

  async function handleAsk() {
    if (!instruction.trim()) return;
    setAsking(true);
    setError(null);
    setResult(null);
    try {
      const res = await notesApi.askAI(encounterId, instruction.trim());
      setResult(res);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Ask AI failed");
    } finally {
      setAsking(false);
    }
  }

  async function handleApply() {
    if (!result?.revised_content) return;
    setApplying(true);
    try {
      await onApply(result.revised_content);
      setResult(null);
      setInstruction("");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to apply revision");
    } finally {
      setApplying(false);
    }
  }

  return (
    <div className="card stack">
      <strong>Ask AI</strong>
      <p style={{ fontSize: 13, color: "var(--color-text-muted)", margin: 0 }}>
        Rework the note ("make this shorter", "translate to French") or look something up
        ("current dosing guidance for X") — Claude figures out which.
      </p>
      <textarea
        className="input"
        rows={2}
        placeholder="What should I do?"
        value={instruction}
        onChange={(e) => setInstruction(e.target.value)}
        disabled={asking}
      />
      <div>
        <button className="btn btn-primary" onClick={handleAsk} disabled={asking || !instruction.trim()}>
          {asking ? "Thinking…" : "Ask AI"}
        </button>
      </div>

      {error && <div className="error-text">{error}</div>}

      {result?.result_type === "revision" && (
        <div className="stack" style={{ borderTop: "1px solid var(--color-border)", paddingTop: 12 }}>
          <span style={{ fontSize: 13, color: "var(--color-text-muted)" }}>Proposed revision:</span>
          <div
            className="input"
            style={{ whiteSpace: "pre-wrap", minHeight: 60, fontFamily: "inherit" }}
          >
            {result.revised_content}
          </div>
          <div className="row">
            <button className="btn btn-primary" onClick={handleApply} disabled={applying}>
              {applying ? "Applying…" : "Apply to note"}
            </button>
            <button className="btn" onClick={() => setResult(null)} disabled={applying}>
              Discard
            </button>
          </div>
        </div>
      )}

      {result?.result_type === "answer" && (
        <div className="stack" style={{ borderTop: "1px solid var(--color-border)", paddingTop: 12 }}>
          <p style={{ margin: 0, fontSize: 14 }}>{result.answer}</p>
          {result.sources.length > 0 && (
            <ul style={{ margin: 0, paddingLeft: 18, fontSize: 13 }}>
              {result.sources.map((s) => (
                <li key={s.url}>
                  <a href={s.url} target="_blank" rel="noreferrer">
                    {s.title}
                  </a>
                </li>
              ))}
            </ul>
          )}
          <div>
            <button className="btn" onClick={() => setResult(null)}>
              Dismiss
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
