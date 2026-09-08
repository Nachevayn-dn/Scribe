import { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { ApiError } from "../api/client";
import * as authApi from "../api/auth";

/** Landing page for the "set your password" link a platform admin sends a
 * newly-provisioned doctor/assistant (see PlatformSettingsPage's Team tab).
 * No login required — the token in the URL is the credential. */
export function SetPasswordPage() {
  const { setPasswordViaLink } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const token = searchParams.get("token") ?? "";

  const [checking, setChecking] = useState(true);
  const [invalidReason, setInvalidReason] = useState<string | null>(null);
  const [info, setInfo] = useState<{ email: string; full_name: string } | null>(null);

  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!token) {
      setInvalidReason("This link is missing its token — ask your admin to send a new one.");
      setChecking(false);
      return;
    }
    authApi
      .checkSetupToken(token)
      .then(setInfo)
      .catch((err) => setInvalidReason(err instanceof ApiError ? err.message : "This link is invalid or has expired."))
      .finally(() => setChecking(false));
  }, [token]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (password !== confirm) {
      setError("Passwords don't match");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await setPasswordViaLink(token, password);
      navigate("/");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't set your password");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="page" style={{ maxWidth: 380, marginTop: 80 }}>
      <div className="card stack">
        <h1 style={{ fontSize: 20, margin: 0 }}>MedicDesk.ai — Set your password</h1>

        {checking && <p style={{ color: "var(--color-text-muted)" }}>Checking your link…</p>}

        {!checking && invalidReason && (
          <>
            <div className="error-text">{invalidReason}</div>
            <div style={{ fontSize: 13 }}>
              <Link to="/login">Back to sign in</Link>
            </div>
          </>
        )}

        {!checking && !invalidReason && info && (
          <>
            <p style={{ margin: 0, fontSize: 14, color: "var(--color-text-muted)" }}>
              Setting a password for <strong>{info.full_name}</strong> ({info.email})
            </p>
            <form className="stack" onSubmit={handleSubmit}>
              <input
                className="input"
                type="password"
                placeholder="New password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                minLength={8}
                required
              />
              <input
                className="input"
                type="password"
                placeholder="Confirm password"
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
                minLength={8}
                required
              />
              {error && <div className="error-text">{error}</div>}
              <button className="btn btn-primary" type="submit" disabled={submitting}>
                {submitting ? "Setting password…" : "Set password & sign in"}
              </button>
            </form>
          </>
        )}
      </div>
    </div>
  );
}
