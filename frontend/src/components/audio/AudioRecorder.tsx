import { useRef, useState } from "react";

interface Props {
  disabled?: boolean;
  onRecordingReady: (blob: Blob, filename: string) => void;
}

export function AudioRecorder({ disabled, onRecordingReady }: Props) {
  const [recording, setRecording] = useState(false);
  const [seconds, setSeconds] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<number | null>(null);

  async function startRecording() {
    setError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mimeType = MediaRecorder.isTypeSupported("audio/webm") ? "audio/webm" : "";
      const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
      chunksRef.current = [];
      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };
      recorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: mimeType || "audio/webm" });
        onRecordingReady(blob, `recording-${Date.now()}.webm`);
        stream.getTracks().forEach((t) => t.stop());
      };
      recorder.start();
      mediaRecorderRef.current = recorder;
      setRecording(true);
      setSeconds(0);
      timerRef.current = window.setInterval(() => setSeconds((s) => s + 1), 1000);
    } catch {
      setError("Microphone access was denied or is unavailable. You can upload a file instead.");
    }
  }

  function stopRecording() {
    mediaRecorderRef.current?.stop();
    setRecording(false);
    if (timerRef.current) window.clearInterval(timerRef.current);
  }

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (file) onRecordingReady(file, file.name);
    e.target.value = "";
  }

  const mm = String(Math.floor(seconds / 60)).padStart(2, "0");
  const ss = String(seconds % 60).padStart(2, "0");

  return (
    <div className="stack">
      <div className="row">
        {!recording ? (
          <button className="btn btn-primary" onClick={startRecording} disabled={disabled}>
            ● Start recording
          </button>
        ) : (
          <button className="btn btn-danger" onClick={stopRecording}>
            ■ Stop ({mm}:{ss})
          </button>
        )}
        <label className="btn" style={{ opacity: disabled ? 0.5 : 1 }}>
          Upload audio file
          <input
            type="file"
            accept="audio/*"
            onChange={handleFileChange}
            disabled={disabled || recording}
            style={{ display: "none" }}
          />
        </label>
      </div>
      {error && <div className="error-text">{error}</div>}
    </div>
  );
}
