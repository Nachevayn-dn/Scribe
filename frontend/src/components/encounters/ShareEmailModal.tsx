import { useState } from "react";
import * as notesApi from "../../api/notes";
import { ApiError } from "../../api/client";
import { useAuth } from "../../auth/AuthContext";
import { Modal } from "../common/Modal";

interface Props {
  encounterId: string;
  contentType: "transcript" | "note";
  onClose: () => void;
}

const LABELS = { transcript: "transcript", note: "note" };

export function ShareEmailModal({ encounterId, contentType, onClose }: Props) {
  const { user } = useAuth();
  const [recipients, setRecipients] = useState("");
  const [includeSelf, setIncludeSelf] = useState(false);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sentTo, setSentTo] = useState<string[] | null>(null);

  const selfEmail = user?.notification_email || user?.email;

  async function handleSend() {
    const list = recipients
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);
    if (list.length === 0 && !includeSelf) {
      setError('Add at least one recipient, or check "send to me"');
      return;
    }
    setSending(true);
    setError(null);
    try {
      const result = await notesApi.shareEncounterContent(encounterId, contentType, list, includeSelf);
      setSentTo(result.recipients);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to send");
    } finally {
      setSending(false);
    }
  }

  return (
    <Modal title={`Share ${LABELS[contentType]} via email`} onClose={onClose}>
      {sentTo ? (
        <div className="stack">
          <p style={{ margin: 0 }}>Sent to {sentTo.join(", ")}.</p>
          <div className="row" style={{ justifyContent: "flex-end" }}>
            <button className="btn btn-primary" onClick={onClose}>
              Close
            </button>
          </div>
        </div>
      ) : (
        <>
          <label className="stack" style={{ gap: 4 }}>
            <span style={{ fontSize: 13, color: "var(--color-text-muted)" }}>
              Recipients (comma-separated)
            </span>
            <input
              className="input"
              value={recipients}
              onChange={(e) => setRecipients(e.target.value)}
              placeholder="staff@example.com, frontdesk@example.com"
            />
          </label>

          <label className="row" style={{ gap: 8, fontSize: 14 }}>
            <input
              type="checkbox"
              checked={includeSelf}
              onChange={(e) => setIncludeSelf(e.target.checked)}
            />
            Also send to me{selfEmail ? ` (${selfEmail})` : ""}
          </label>

          {error && <div className="error-text">{error}</div>}

          <div className="row" style={{ justifyContent: "flex-end" }}>
            <button className="btn" onClick={onClose}>
              Cancel
            </button>
            <button className="btn btn-primary" disabled={sending} onClick={handleSend}>
              {sending ? "Sending…" : "Send"}
            </button>
          </div>
        </>
      )}
    </Modal>
  );
}
