import { useState } from "react";
import { Modal } from "../../components/common/Modal";

const SUPPORT_EMAIL = "support@medicdesk.ai";

/** Opens the viewer's own mail client with a pre-filled message — no backend
 * needed, works everywhere, and doesn't depend on Resend being configured. */
export function HelpFeedbackModal({ onClose }: { onClose: () => void }) {
  const [subject, setSubject] = useState("");
  const [message, setMessage] = useState("");

  function handleSend() {
    const params = new URLSearchParams({
      subject: subject.trim() || "MedicDesk.ai feedback",
      body: message,
    });
    window.location.href = `mailto:${SUPPORT_EMAIL}?${params.toString()}`;
    onClose();
  }

  return (
    <Modal title="Help / Feedback" onClose={onClose}>
      <label className="stack" style={{ gap: 4 }}>
        <span style={{ fontSize: 13, color: "var(--color-text-muted)" }}>Subject</span>
        <input className="input" value={subject} onChange={(e) => setSubject(e.target.value)} placeholder="What's this about?" />
      </label>

      <label className="stack" style={{ gap: 4 }}>
        <span style={{ fontSize: 13, color: "var(--color-text-muted)" }}>Message</span>
        <textarea
          className="input"
          rows={5}
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          placeholder="Describe the issue or your feedback…"
        />
      </label>

      <p style={{ fontSize: 12, color: "var(--color-text-muted)", margin: 0 }}>
        Opens your email app addressed to {SUPPORT_EMAIL}.
      </p>

      <div className="row" style={{ justifyContent: "flex-end" }}>
        <button className="btn" onClick={onClose}>
          Cancel
        </button>
        <button className="btn btn-primary" onClick={handleSend}>
          Open email
        </button>
      </div>
    </Modal>
  );
}
