import { useRef, useState } from "react";
import * as usersApi from "../../api/users";
import { useAuth } from "../../auth/AuthContext";

function initials(fullName: string): string {
  const parts = fullName.trim().split(/\s+/);
  return parts.slice(0, 2).map((p) => p[0]?.toUpperCase() ?? "").join("");
}

/** Circular profile photo, click-to-upload. Wraps a hidden file input over
 * the visual — same pattern as AudioRecorder's "Upload audio file" button. */
export function DoctorAvatar({ size = 40 }: { size?: number }) {
  const { user, refreshUser } = useAuth();
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  if (!user) return null;

  async function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setError(null);
    try {
      await usersApi.uploadMyPhoto(file);
      await refreshUser();
    } catch {
      setError("Upload failed");
    } finally {
      setUploading(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  }

  return (
    <label
      title={uploading ? "Uploading…" : "Click to change your photo"}
      style={{
        position: "relative",
        width: size,
        height: size,
        borderRadius: "50%",
        overflow: "hidden",
        flexShrink: 0,
        cursor: "pointer",
        border: "2px solid var(--color-primary)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        background: "var(--color-surface-hover)",
        color: "var(--color-primary)",
        fontWeight: 700,
        fontSize: size * 0.38,
        opacity: uploading ? 0.6 : 1,
      }}
    >
      {user.photo_url ? (
        <img
          src={user.photo_url}
          alt={user.full_name}
          style={{ width: "100%", height: "100%", objectFit: "cover" }}
        />
      ) : (
        initials(user.full_name)
      )}
      <input
        ref={inputRef}
        type="file"
        accept="image/*"
        onChange={handleFileChange}
        disabled={uploading}
        style={{ display: "none" }}
      />
      {error && (
        <span
          className="error-text"
          style={{ position: "absolute", top: size + 4, left: 0, fontSize: 11, whiteSpace: "nowrap" }}
        >
          {error}
        </span>
      )}
    </label>
  );
}
