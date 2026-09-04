import { useState } from "react";
import * as usersApi from "../../api/users";
import { useAuth } from "../../auth/AuthContext";
import { EU_LANGUAGES } from "../../data/languages";
import { Modal } from "./Modal";

/** Shown once, the first time a doctor logs in with no default language set
 * yet (e.g. right after a platform admin generates their credentials — see
 * the /platform console). Renders nothing once language_preference is set. */
export function FirstLoginLanguageModal() {
  const { user, refreshUser } = useAuth();
  const [code, setCode] = useState("en");
  const [saving, setSaving] = useState(false);

  if (!user || user.language_preference) return null;

  async function handleSave() {
    setSaving(true);
    try {
      await usersApi.updateMyPreferences({ language_preference: code });
      await refreshUser();
    } finally {
      setSaving(false);
    }
  }

  return (
    <Modal title="Welcome to MedicDesk.ai" onClose={handleSave}>
      <p style={{ margin: 0, fontSize: 14 }}>Pick your default language to get started.</p>
      <select className="input" value={code} onChange={(e) => setCode(e.target.value)}>
        {EU_LANGUAGES.map((l) => (
          <option key={l.code} value={l.code}>
            {l.label}
          </option>
        ))}
      </select>
      <div className="row" style={{ justifyContent: "flex-end" }}>
        <button className="btn btn-primary" disabled={saving} onClick={handleSave}>
          {saving ? "Saving…" : "Continue"}
        </button>
      </div>
    </Modal>
  );
}
