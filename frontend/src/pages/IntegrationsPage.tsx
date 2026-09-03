import { useEffect, useState } from "react";
import * as clinicsApi from "../api/clinics";
import * as usersApi from "../api/users";
import { useAuth } from "../auth/AuthContext";
import { ApiError } from "../api/client";
import type { Clinic } from "../types";

export function IntegrationsPage() {
  const { user, refreshUser } = useAuth();
  const [clinic, setClinic] = useState<Clinic | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState<string | null>(null);

  const [notificationEmail, setNotificationEmail] = useState("");
  const [contactEmail, setContactEmail] = useState("");
  const [staffEmail, setStaffEmail] = useState("");
  const [savingEmail, setSavingEmail] = useState(false);

  const isAdmin = user?.role === "SUPER_ADMIN";

  useEffect(() => {
    (async () => {
      try {
        const c = await clinicsApi.getMyClinic();
        setClinic(c);
        setContactEmail(c.contact_email ?? "");
        setStaffEmail(c.staff_email ?? "");
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "Failed to load clinic settings");
      } finally {
        setLoading(false);
      }
    })();
    setNotificationEmail(user?.notification_email ?? "");
  }, [user?.notification_email]);

  async function handleSaveEmail(e: React.FormEvent) {
    e.preventDefault();
    setSavingEmail(true);
    setError(null);
    setSaved(null);
    try {
      if (notificationEmail.trim()) {
        await usersApi.updateMyPreferences({ notification_email: notificationEmail.trim() });
        await refreshUser();
      }
      if (isAdmin) {
        const updated = await clinicsApi.updateMyClinic({
          contact_email: contactEmail.trim() || undefined,
          staff_email: staffEmail.trim() || undefined,
        });
        setClinic(updated);
      }
      setSaved("Saved.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to save email settings");
    } finally {
      setSavingEmail(false);
    }
  }

  if (loading) return <div className="page">Loading…</div>;

  return (
    <div className="page stack">
      <h1 style={{ fontSize: 22 }}>Integrations</h1>
      <p style={{ color: "var(--color-text-muted)", fontSize: 14, marginTop: -8 }}>
        Where MedicDesk.ai sends things, and what it connects to.
      </p>

      {error && <div className="error-text">{error}</div>}

      <form className="card stack" onSubmit={handleSaveEmail}>
        <strong>Email</strong>
        <p style={{ fontSize: 13, color: "var(--color-text-muted)", margin: 0 }}>
          Used when sharing a transcript or note — see "Share via email" on a Scribe session.
          Replies go to whichever address sent the share, so recipients can write back.
        </p>

        <label className="stack" style={{ gap: 4, maxWidth: 420 }}>
          <span style={{ fontSize: 13, color: "var(--color-text-muted)" }}>
            Your notification email
          </span>
          <input
            className="input"
            type="email"
            placeholder={user?.email}
            value={notificationEmail}
            onChange={(e) => setNotificationEmail(e.target.value)}
          />
          <span style={{ fontSize: 12, color: "var(--color-text-muted)" }}>
            Where shares land when you check "send to me." Defaults to your login email
            ({user?.email}) if left blank.
          </span>
        </label>

        {isAdmin && (
          <>
            <hr style={{ border: "none", borderTop: "1px solid var(--color-border)", width: "100%" }} />
            <label className="stack" style={{ gap: 4, maxWidth: 420 }}>
              <span style={{ fontSize: 13, color: "var(--color-text-muted)" }}>Clinic email</span>
              <input
                className="input"
                type="email"
                placeholder="clinic@example.com"
                value={contactEmail}
                onChange={(e) => setContactEmail(e.target.value)}
              />
            </label>
            <label className="stack" style={{ gap: 4, maxWidth: 420 }}>
              <span style={{ fontSize: 13, color: "var(--color-text-muted)" }}>
                Staff email (scheduling / EHR entry)
              </span>
              <input
                className="input"
                type="email"
                placeholder="frontdesk@example.com"
                value={staffEmail}
                onChange={(e) => setStaffEmail(e.target.value)}
              />
              <span style={{ fontSize: 12, color: "var(--color-text-muted)" }}>
                Suggested by default as a recipient when a doctor shares a session summary, so
                staff can schedule follow-ups or copy it into the EHR.
              </span>
            </label>
          </>
        )}

        <div className="row">
          <button className="btn btn-primary" type="submit" disabled={savingEmail}>
            {savingEmail ? "Saving…" : "Save"}
          </button>
          {saved && <span style={{ fontSize: 13, color: "var(--color-text-muted)" }}>{saved}</span>}
        </div>
      </form>

      <div className="card stack">
        <strong>Calendar</strong>
        <div className="row" style={{ justifyContent: "space-between", flexWrap: "wrap" }}>
          <p style={{ fontSize: 13, color: "var(--color-text-muted)", margin: 0, maxWidth: 480 }}>
            Sync scheduled appointments with Google Calendar automatically. Not connected yet —
            for now, mark a Scribe session as "for a scheduled appointment" (with a date &amp;
            time) when you start it, and it's counted on your dashboard.
          </p>
          <button className="btn" disabled title="Coming soon">
            Connect Google Calendar
          </button>
        </div>
      </div>
    </div>
  );
}
