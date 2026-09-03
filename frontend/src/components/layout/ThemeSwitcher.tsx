import { useState } from "react";
import * as usersApi from "../../api/users";
import { useAuth } from "../../auth/AuthContext";
import type { ThemePreference } from "../../types";

const SWATCHES: { value: ThemePreference; label: string; color: string }[] = [
  { value: "midnight", label: "Midnight (amber)", color: "#e0a83a" },
  { value: "jade", label: "Jade & Candlelight", color: "#1f6f54" },
];

/** Two small color swatches — click to switch the app's color scheme.
 * Persisted per-doctor via PATCH /users/me (see Integrations for the fuller
 * settings surface; this is the always-in-reach shortcut). */
export function ThemeSwitcher() {
  const { user, refreshUser } = useAuth();
  const [saving, setSaving] = useState<ThemePreference | null>(null);

  if (!user) return null;

  async function handlePick(value: ThemePreference) {
    if (value === user!.theme_preference || saving) return;
    setSaving(value);
    try {
      await usersApi.updateMyPreferences({ theme_preference: value });
      await refreshUser();
    } finally {
      setSaving(null);
    }
  }

  return (
    <div className="row" style={{ gap: 4 }} role="group" aria-label="Color scheme">
      {SWATCHES.map((s) => {
        const active = user.theme_preference === s.value;
        return (
          <button
            key={s.value}
            onClick={() => handlePick(s.value)}
            title={s.label}
            aria-label={s.label}
            aria-pressed={active}
            disabled={saving !== null}
            style={{
              width: 20,
              height: 20,
              borderRadius: "50%",
              background: s.color,
              border: active ? "2px solid var(--color-text)" : "2px solid transparent",
              boxShadow: active ? "none" : "0 0 0 1px var(--color-border)",
              cursor: saving ? "wait" : "pointer",
              padding: 0,
              opacity: saving && saving !== s.value ? 0.5 : 1,
            }}
          />
        );
      })}
    </div>
  );
}
