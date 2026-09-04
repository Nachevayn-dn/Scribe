import { useState } from "react";
import * as usersApi from "../../api/users";
import { useAuth } from "../../auth/AuthContext";
import { ThemeSwitcher } from "../../components/layout/ThemeSwitcher";
import { ApiError } from "../../api/client";
import { EU_LANGUAGES } from "../../data/languages";

/** The platform admin's own preferences — color scheme, notification email,
 * default language. Distinct from a doctor's clinical trigger-phrase
 * preferences (see PreferencesSettingsPage). */
export function PlatformPreferencesPage() {
  const { user, refreshUser } = useAuth();
  const [notificationEmail, setNotificationEmail] = useState(user?.notification_email ?? "");
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function handleSaveEmail(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    setSaved(null);
    try {
      await usersApi.updateMyPreferences({ notification_email: notificationEmail.trim() || undefined });
      await refreshUser();
      setSaved("Saved.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to save");
    } finally {
      setSaving(false);
    }
  }

  async function handleLanguageChange(code: string) {
    try {
      await usersApi.updateMyPreferences({ language_preference: code });
      await refreshUser();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to save");
    }
  }

  return (
    <div className="stack">
      <h1 style={{ fontSize: 22 }}>Preferences</h1>

      {error && <div className="error-text">{error}</div>}

      <div className="card stack">
        <strong>Color scheme</strong>
        <ThemeSwitcher />
      </div>

      <div className="card stack">
        <strong>Default language</strong>
        <select
          className="input"
          style={{ maxWidth: 240 }}
          value={user?.language_preference ?? "en"}
          onChange={(e) => handleLanguageChange(e.target.value)}
        >
          {EU_LANGUAGES.map((l) => (
            <option key={l.code} value={l.code}>
              {l.label}
            </option>
          ))}
        </select>
      </div>

      <form className="card stack" onSubmit={handleSaveEmail}>
        <strong>Notification email</strong>
        <input
          className="input"
          type="email"
          placeholder={user?.email}
          value={notificationEmail}
          onChange={(e) => setNotificationEmail(e.target.value)}
          style={{ maxWidth: 320 }}
        />
        <div className="row">
          <button className="btn btn-primary" type="submit" disabled={saving}>
            {saving ? "Saving…" : "Save"}
          </button>
          {saved && <span style={{ fontSize: 13, color: "var(--color-text-muted)" }}>{saved}</span>}
        </div>
      </form>
    </div>
  );
}
