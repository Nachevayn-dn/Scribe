import { useEffect, useState } from "react";
import * as templatesApi from "../api/templates";
import { useAuth } from "../auth/AuthContext";
import { ApiError } from "../api/client";
import { EU_LANGUAGES } from "../data/languages";
import type { NoteTemplate } from "../types";

const NON_ENGLISH_LANGUAGES = EU_LANGUAGES.filter((l) => l.code !== "en");

/** Lets a doctor create their own note templates (e.g. an insurance-specific
 * format with its own section names/codes — the backend has supported this
 * since Milestone 5, this page was the missing piece) and, per template,
 * confirm/edit the section-title translation used automatically whenever a
 * session in that language uses this template. */
export function TemplatesPage() {
  const { user } = useAuth();
  const [templates, setTemplates] = useState<NoteTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [name, setName] = useState("");
  const [structureText, setStructureText] = useState("");
  const [saving, setSaving] = useState(false);

  const [translatingId, setTranslatingId] = useState<string | null>(null);

  async function refresh() {
    setLoading(true);
    try {
      setTemplates(await templatesApi.listTemplates());
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load templates");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  function canEdit(t: NoteTemplate): boolean {
    if (t.clinic_id === null) return false; // system template — shared, not editable
    if (user?.role === "SUPER_ADMIN") return true;
    return t.created_by_id === user?.id;
  }

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    const structure = structureText
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);
    if (!name.trim() || structure.length === 0) return;
    setSaving(true);
    setError(null);
    try {
      await templatesApi.createTemplate({ name: name.trim(), template_type: "CUSTOM", structure });
      setName("");
      setStructureText("");
      await refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to create template");
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(t: NoteTemplate) {
    if (!window.confirm(`Delete template "${t.name}"?`)) return;
    try {
      await templatesApi.deleteTemplate(t.id);
      await refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to delete template");
    }
  }

  if (loading) return <div className="page">Loading…</div>;

  return (
    <div className="page stack">
      <h1 style={{ fontSize: 22 }}>Note templates</h1>
      <p style={{ fontSize: 13, color: "var(--color-text-muted)", margin: 0 }}>
        Build your own note format — an insurance-specific layout with its own section names and
        codes, for example. Pick it from the template selector whenever you generate a note.
      </p>

      <form className="card row" onSubmit={handleCreate} style={{ flexWrap: "wrap" }}>
        <input
          className="input"
          placeholder="Template name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          style={{ width: 220 }}
          required
        />
        <input
          className="input"
          placeholder="Section names, comma-separated (e.g. Chief Complaint, Diagnosis Codes, Procedure Codes, Next Steps)"
          value={structureText}
          onChange={(e) => setStructureText(e.target.value)}
          style={{ flex: 1, minWidth: 320 }}
          required
        />
        <button className="btn btn-primary" type="submit" disabled={saving}>
          {saving ? "Saving…" : "+ New template"}
        </button>
      </form>

      {error && <div className="error-text">{error}</div>}

      <div className="stack">
        {templates.map((t) => (
          <div key={t.id} className="card stack">
            <div className="row" style={{ justifyContent: "space-between" }}>
              <div className="row">
                <strong>{t.name}</strong>
                <span className="badge">{t.clinic_id === null ? "Shared" : "Custom"}</span>
              </div>
              <div className="row">
                <button
                  className="btn"
                  onClick={() => setTranslatingId(translatingId === t.id ? null : t.id)}
                >
                  {translatingId === t.id ? "Close" : "Section title translations"}
                </button>
                {canEdit(t) && (
                  <button className="btn" onClick={() => handleDelete(t)}>
                    Delete
                  </button>
                )}
              </div>
            </div>
            <p style={{ margin: 0, fontSize: 13, color: "var(--color-text-muted)" }}>
              {t.structure.join(" → ")}
            </p>

            {translatingId === t.id && <TemplateTranslationPanel template={t} />}
          </div>
        ))}
        {templates.length === 0 && <div className="card">No templates yet.</div>}
      </div>
    </div>
  );
}

function TemplateTranslationPanel({ template }: { template: NoteTemplate }) {
  const [language, setLanguage] = useState(NON_ENGLISH_LANGUAGES[0]?.code ?? "");
  const [titles, setTitles] = useState<string[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [isConfirmed, setIsConfirmed] = useState(false);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  async function handleLoad() {
    setLoading(true);
    setError(null);
    setSaved(false);
    try {
      const draft = await templatesApi.getTemplateTranslation(template.id, language);
      setTitles(draft.translated_structure);
      setIsConfirmed(draft.is_confirmed);
      setLoaded(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load translation");
    } finally {
      setLoading(false);
    }
  }

  async function handleSave() {
    setSaving(true);
    setError(null);
    try {
      await templatesApi.confirmTemplateTranslation(template.id, language, titles);
      setIsConfirmed(true);
      setSaved(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to save translation");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="stack" style={{ borderTop: "1px solid var(--color-border)", paddingTop: 10 }}>
      <div className="row" style={{ flexWrap: "wrap" }}>
        <select
          className="input"
          value={language}
          onChange={(e) => {
            setLanguage(e.target.value);
            setLoaded(false);
            setSaved(false);
          }}
          style={{ width: 180 }}
        >
          {NON_ENGLISH_LANGUAGES.map((l) => (
            <option key={l.code} value={l.code}>
              {l.label}
            </option>
          ))}
        </select>
        <button className="btn" onClick={handleLoad} disabled={loading}>
          {loading ? "Loading…" : isConfirmed && loaded ? "Reload" : "Load / suggest"}
        </button>
      </div>

      {loaded && (
        <>
          <p style={{ fontSize: 12, color: "var(--color-text-muted)", margin: 0 }}>
            {isConfirmed
              ? "Confirmed — used automatically for future sessions in this language with this template."
              : "Suggested translation — review and edit each title, then save to confirm it."}
          </p>
          <div className="stack" style={{ gap: 6 }}>
            {template.structure.map((original, i) => (
              <div key={i} className="row" style={{ gap: 8, alignItems: "center" }}>
                <span style={{ fontSize: 12, color: "var(--color-text-muted)", width: 160 }}>{original}</span>
                <input
                  className="input"
                  value={titles[i] ?? ""}
                  onChange={(e) => setTitles((prev) => prev.map((t, idx) => (idx === i ? e.target.value : t)))}
                  style={{ flex: 1 }}
                />
              </div>
            ))}
          </div>
          <div className="row" style={{ justifyContent: "flex-end" }}>
            <button className="btn btn-primary" onClick={handleSave} disabled={saving}>
              {saving ? "Saving…" : saved ? "Saved ✓" : "Save translation"}
            </button>
          </div>
        </>
      )}

      {error && <div className="error-text">{error}</div>}
    </div>
  );
}
