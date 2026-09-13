import { useEffect, useState } from "react";
import * as clinicsApi from "../api/clinics";
import * as usersApi from "../api/users";
import { useAuth } from "../auth/AuthContext";
import { ApiError } from "../api/client";
import { BillingCard } from "../components/settings/BillingCard";
import { EU_LANGUAGES } from "../data/languages";
import type { Clinic } from "../types";

/** The doctor's (or clinic admin's) own settings: personal preferences
 * (language, notification email) plus, for a PROVIDER/SUPER_ADMIN, the
 * inbound agent's greeting for their own clinic. Everything else about
 * the phone line — pickup mode, phone number, knowledge base — stays
 * under the platform console. Also embedded as the "Integrations" tab
 * inside the Platform Settings console, where it edits the logged-in
 * platform admin's own account the same way. */
export function SettingsPage() {
  const { user, refreshUser } = useAuth();
  const [clinic, setClinic] = useState<Clinic | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState<string | null>(null);

  const [language, setLanguage] = useState("en");
  const [notificationEmail, setNotificationEmail] = useState("");
  const [contactEmail, setContactEmail] = useState("");
  const [staffEmail, setStaffEmail] = useState("");
  const [savingProfile, setSavingProfile] = useState(false);

  const [greeting, setGreeting] = useState("");
  const [savingGreeting, setSavingGreeting] = useState(false);
  const [greetingSaved, setGreetingSaved] = useState<string | null>(null);

  const isAdmin = user?.role === "SUPER_ADMIN";
  const canEditGreeting = user?.role === "PROVIDER" || user?.role === "SUPER_ADMIN";

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
    setLanguage(user?.language_preference ?? "en");
  }, [user?.notification_email, user?.language_preference]);

  useEffect(() => {
    if (!canEditGreeting) return;
    (async () => {
      try {
        const g = await clinicsApi.getMyClinicGreeting();
        setGreeting(g.greeting_text);
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "Failed to load greeting");
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [canEditGreeting]);

  async function handleSaveProfile(e: React.FormEvent) {
    e.preventDefault();
    setSavingProfile(true);
    setError(null);
    setSaved(null);
    try {
      await usersApi.updateMyPreferences({
        language_preference: language,
        notification_email: notificationEmail.trim() || undefined,
      });
      await refreshUser();
      if (isAdmin) {
        const updated = await clinicsApi.updateMyClinic({
          contact_email: contactEmail.trim() || undefined,
          staff_email: staffEmail.trim() || undefined,
        });
        setClinic(updated);
      }
      setSaved("Saved.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to save settings");
    } finally {
      setSavingProfile(false);
    }
  }

  async function handleSaveGreeting(e: React.FormEvent) {
    e.preventDefault();
    setSavingGreeting(true);
    setError(null);
    setGreetingSaved(null);
    try {
      await clinicsApi.updateMyClinicGreeting(greeting);
      setGreetingSaved("Saved.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to save greeting");
    } finally {
      setSavingGreeting(false);
    }
  }

  // Lets the account menu's "Payment details" link (/settings#billing) jump
  // straight to that card instead of just landing at the top of the page.
  useEffect(() => {
    if (!loading && window.location.hash === "#billing") {
      document.getElementById("billing")?.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }, [loading]);

  if (loading) return <div className="page">Loading…</div>;

  return (
    <div className="page stack">
      <h1 style={{ fontSize: 22 }}>Settings</h1>
      <p style={{ color: "var(--color-text-muted)", fontSize: 14, marginTop: -8 }}>
        Your preferences, and where MedicDesk.ai sends things.
      </p>

      {error && <div className="error-text">{error}</div>}

      <form className="card stack" onSubmit={handleSaveProfile}>
        <strong>Profile</strong>

        <label className="stack" style={{ gap: 4, maxWidth: 300 }}>
          <span style={{ fontSize: 13, color: "var(--color-text-muted)" }}>Language</span>
          <select className="input" value={language} onChange={(e) => setLanguage(e.target.value)}>
            {EU_LANGUAGES.map((l) => (
              <option key={l.code} value={l.code}>
                {l.label}
              </option>
            ))}
          </select>
        </label>

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
            Where shares land when you check "send to me," and where a proposed appointment's
            confirmation goes if it's sent by email. Defaults to your login email ({user?.email})
            if left blank.
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
          <button className="btn btn-primary" type="submit" disabled={savingProfile}>
            {savingProfile ? "Saving…" : "Save"}
          </button>
          {saved && <span style={{ fontSize: 13, color: "var(--color-text-muted)" }}>{saved}</span>}
        </div>
      </form>

      {canEditGreeting && (
        <form className="card stack" onSubmit={handleSaveGreeting}>
          <strong>Inbound agent greeting</strong>
          <p style={{ fontSize: 13, color: "var(--color-text-muted)", margin: 0 }}>
            What the AI receptionist says at the start of every call to{" "}
            {clinic ? clinic.name : "your clinic"}.
          </p>
          <textarea
            className="input"
            rows={2}
            value={greeting}
            onChange={(e) => setGreeting(e.target.value)}
          />
          <div className="row">
            <button className="btn btn-primary" type="submit" disabled={savingGreeting}>
              {savingGreeting ? "Saving…" : "Save"}
            </button>
            {greetingSaved && (
              <span style={{ fontSize: 13, color: "var(--color-text-muted)" }}>{greetingSaved}</span>
            )}
          </div>
        </form>
      )}

      {isAdmin && <BillingCard />}

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
