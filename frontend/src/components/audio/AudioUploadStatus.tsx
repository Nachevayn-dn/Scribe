import type { EncounterStatus } from "../../types";

const LABELS: Record<EncounterStatus, string> = {
  IN_PROGRESS: "Ready to record",
  TRANSCRIBING: "Transcribing audio…",
  TRANSCRIPT_READY: "Transcript ready — review below",
  EXTRACTING: "Generating clinical note…",
  NOTE_READY: "Note ready",
  SIGNED: "Note signed",
  FAILED: "Something went wrong",
};

export function AudioUploadStatus({
  status,
  failureReason,
}: {
  status: EncounterStatus;
  failureReason?: string | null;
}) {
  const busy = status === "TRANSCRIBING" || status === "EXTRACTING";
  return (
    <div className="row">
      {busy && <span className="spinner" aria-hidden>⏳</span>}
      <span>{LABELS[status]}</span>
      {status === "FAILED" && failureReason && (
        <span className="error-text">— {failureReason}</span>
      )}
    </div>
  );
}
