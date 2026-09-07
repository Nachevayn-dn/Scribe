import { useEffect, useState } from "react";
import * as outboundConfigApi from "../../api/outboundConfig";
import { ApiError } from "../../api/client";
import { EU_LANGUAGES } from "../../data/languages";
import type { Clinic, OutboundAgentConfig } from "../../types";

/** When pre-procedure check-ins go out and on which channels, for one
 * clinic's outbound agent. The appointment-confirmation send itself
 * (triggered by a doctor's "Approve appointment" click) needs no settings
 * here beyond enabled + channel toggles — it always fires immediately. */
export function OutboundSettingsTab({ clinic }: { clinic: Clinic }) {
  const [config, setConfig] = useState<OutboundAgentConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function refresh() {
    setLoading(true);
    try {
      setConfig(await outboundConfigApi.getOutboundConfig(clinic.id));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load outbound settings");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
    setSaved(null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [clinic.id]);

  async function handleSave() {
    if (!config) return;
    setSaving(true);
    setError(null);
    setSaved(null);
    try {
      const updated = await outboundConfigApi.updateOutboundConfig(clinic.id, {
        enabled: config.enabled,
        day_before_enabled: config.day_before_enabled,
        day_before_send_hour: config.day_before_send_hour,
        hours_before_enabled: config.hours_before_enabled,
        hours_before_offset: config.hours_before_offset,
        default_language: config.default_language,
        additional_languages: config.additional_languages,
        email_enabled: config.email_enabled,
        sms_enabled: config.sms_enabled,
        whatsapp_enabled: config.whatsapp_enabled,
      });
      setConfig(updated);
      setSaved("Saved.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to save");
    } finally {
      setSaving(false);
    }
  }

  function toggleLanguage(code: string) {
    if (!config) return;
    const has = config.additional_languages.includes(code);
    setConfig({
      ...config,
      additional_languages: has
        ? config.additional_languages.filter((c) => c !== code)
        : [...config.additional_languages, code],
    });
  }

  if (loading || !config) return <div className="card">Loading…</div>;

  return (
    <div className="stack">
      {error && <div className="error-text">{error}</div>}

      <div className="card stack">
        <label className="row" style={{ gap: 8 }}>
          <input type="checkbox" checked={config.enabled} onChange={(e) => setConfig({ ...config, enabled: e.target.checked })} />
          Outbound agent enabled
        </label>
        <p style={{ margin: 0, fontSize: 13, color: "var(--color-text-muted)" }}>
          Sends the appointment confirmation the moment a doctor approves a proposed slot, plus the
          pre-procedure check-ins below.
        </p>
      </div>

      <div className="card stack">
        <strong>Channels</strong>
        <div className="row" style={{ flexWrap: "wrap", gap: 16 }}>
          <label className="row" style={{ gap: 4, fontSize: 13 }}>
            <input type="checkbox" checked={config.email_enabled} onChange={(e) => setConfig({ ...config, email_enabled: e.target.checked })} />
            Email
          </label>
          <label className="row" style={{ gap: 4, fontSize: 13 }}>
            <input type="checkbox" checked={config.sms_enabled} onChange={(e) => setConfig({ ...config, sms_enabled: e.target.checked })} />
            SMS
          </label>
          <label className="row" style={{ gap: 4, fontSize: 13 }}>
            <input type="checkbox" checked={config.whatsapp_enabled} onChange={(e) => setConfig({ ...config, whatsapp_enabled: e.target.checked })} />
            WhatsApp
          </label>
        </div>
        <p style={{ margin: 0, fontSize: 12, color: "var(--color-text-muted)" }}>
          The agent always tries the channel the patient used during their inbound call first.
        </p>
      </div>

      <div className="card stack">
        <strong>Pre-procedure check-ins</strong>
        <label className="row" style={{ gap: 8 }}>
          <input
            type="checkbox"
            checked={config.day_before_enabled}
            onChange={(e) => setConfig({ ...config, day_before_enabled: e.target.checked })}
          />
          Day-before reminder
        </label>
        {config.day_before_enabled && (
          <label className="stack" style={{ gap: 4, maxWidth: 200 }}>
            <span style={{ fontSize: 13, color: "var(--color-text-muted)" }}>Sent at</span>
            <input
              className="input"
              type="time"
              value={config.day_before_send_hour.slice(0, 5)}
              onChange={(e) => setConfig({ ...config, day_before_send_hour: `${e.target.value}:00` })}
            />
          </label>
        )}

        <label className="row" style={{ gap: 8 }}>
          <input
            type="checkbox"
            checked={config.hours_before_enabled}
            onChange={(e) => setConfig({ ...config, hours_before_enabled: e.target.checked })}
          />
          Hours-before reminder
        </label>
        {config.hours_before_enabled && (
          <label className="stack" style={{ gap: 4, maxWidth: 200 }}>
            <span style={{ fontSize: 13, color: "var(--color-text-muted)" }}>Hours before the appointment</span>
            <input
              className="input"
              type="number"
              min={1}
              max={48}
              value={config.hours_before_offset}
              onChange={(e) => setConfig({ ...config, hours_before_offset: Number(e.target.value) })}
            />
          </label>
        )}
      </div>

      <div className="card stack">
        <strong>Language</strong>
        <label className="stack" style={{ gap: 4, maxWidth: 240 }}>
          <span style={{ fontSize: 13, color: "var(--color-text-muted)" }}>Default language</span>
          <select className="input" value={config.default_language} onChange={(e) => setConfig({ ...config, default_language: e.target.value })}>
            {EU_LANGUAGES.map((l) => (
              <option key={l.code} value={l.code}>
                {l.label}
              </option>
            ))}
          </select>
        </label>
        <span style={{ fontSize: 13, color: "var(--color-text-muted)" }}>Also writes in:</span>
        <div className="row" style={{ flexWrap: "wrap", gap: 8 }}>
          {EU_LANGUAGES.filter((l) => l.code !== config.default_language).map((l) => (
            <label key={l.code} className="row" style={{ gap: 4, fontSize: 13 }}>
              <input type="checkbox" checked={config.additional_languages.includes(l.code)} onChange={() => toggleLanguage(l.code)} />
              {l.label}
            </label>
          ))}
        </div>
      </div>

      <div className="row">
        <button className="btn btn-primary" disabled={saving} onClick={handleSave}>
          {saving ? "Saving…" : "Save"}
        </button>
        {saved && <span style={{ fontSize: 13, color: "var(--color-text-muted)" }}>{saved}</span>}
      </div>
    </div>
  );
}
