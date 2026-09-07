import { useEffect, useState } from "react";
import * as telephonyApi from "../../api/telephony";
import { ApiError } from "../../api/client";
import { EU_LANGUAGES } from "../../data/languages";
import type { Clinic, ContactChannel, InboundAgentConfig, PickupMode, SummaryShareWith } from "../../types";

/** Twilio connection, pickup rules, language, greeting, recording, and
 * summary-sharing settings for one clinic's inbound agent. */
export function TelephonyTab({ clinic }: { clinic: Clinic }) {
  const [config, setConfig] = useState<InboundAgentConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState<string | null>(null);
  const [provisioning, setProvisioning] = useState(false);
  const [connectingWhatsApp, setConnectingWhatsApp] = useState(false);
  const [saving, setSaving] = useState(false);

  async function refresh() {
    setLoading(true);
    try {
      setConfig(await telephonyApi.getTelephonyConfig(clinic.id));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load telephony settings");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
    setSaved(null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [clinic.id]);

  async function handleProvision() {
    setProvisioning(true);
    setError(null);
    try {
      await telephonyApi.provisionPhoneNumber(clinic.id);
      await refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to provision a phone number");
    } finally {
      setProvisioning(false);
    }
  }

  async function handleConnectWhatsApp() {
    setConnectingWhatsApp(true);
    setError(null);
    try {
      await telephonyApi.connectWhatsApp(clinic.id);
      await refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to connect WhatsApp");
    } finally {
      setConnectingWhatsApp(false);
    }
  }

  async function handleSave() {
    if (!config) return;
    setSaving(true);
    setError(null);
    setSaved(null);
    try {
      const updated = await telephonyApi.updateTelephonyConfig(clinic.id, {
        enabled: config.enabled,
        default_language: config.default_language,
        additional_languages: config.additional_languages,
        greeting_text: config.greeting_text,
        pickup_mode: config.pickup_mode,
        after_hours_start: config.after_hours_start,
        after_hours_end: config.after_hours_end,
        no_answer_timeout_seconds: config.no_answer_timeout_seconds,
        forward_to_number: config.forward_to_number,
        recording_enabled: config.recording_enabled,
        share_summary_with: config.share_summary_with,
        share_channel: config.share_channel,
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
        <strong>Phone number</strong>
        {config.phone_number ? (
          <p style={{ margin: 0 }}>
            Connected: <strong>{config.phone_number}</strong>
          </p>
        ) : (
          <>
            <p style={{ margin: 0, fontSize: 13, color: "var(--color-text-muted)" }}>
              No number yet. Generating one buys a real Twilio phone number — this is a real, billed
              charge on your own Twilio account (a few dollars a month plus usage), not free.
            </p>
            <div>
              <button className="btn btn-primary" disabled={provisioning} onClick={handleProvision}>
                {provisioning ? "Generating…" : "Generate phone number"}
              </button>
            </div>
          </>
        )}
      </div>

      <div className="card stack">
        <strong>WhatsApp</strong>
        {config.whatsapp_number ? (
          <p style={{ margin: 0 }}>
            Connected: <strong>{config.whatsapp_number}</strong>
            {config.whatsapp_number === "whatsapp:+14155238886" && (
              <span style={{ color: "var(--color-text-muted)" }}> (Twilio's shared testing sandbox)</span>
            )}
          </p>
        ) : (
          <>
            <p style={{ margin: 0, fontSize: 13, color: "var(--color-text-muted)" }}>
              Connects Twilio's free sandbox number for testing. Swap in your own Meta-verified WhatsApp
              Business number later — no code changes needed.
            </p>
            <div>
              <button className="btn" disabled={connectingWhatsApp} onClick={handleConnectWhatsApp}>
                {connectingWhatsApp ? "Connecting…" : "Connect WhatsApp sandbox"}
              </button>
            </div>
          </>
        )}
      </div>

      <div className="card stack">
        <strong>Pickup</strong>
        <label className="row" style={{ gap: 8 }}>
          <input type="checkbox" checked={config.enabled} onChange={(e) => setConfig({ ...config, enabled: e.target.checked })} />
          Inbound agent enabled
        </label>

        <label className="stack" style={{ gap: 4, maxWidth: 320 }}>
          <span style={{ fontSize: 13, color: "var(--color-text-muted)" }}>When does the agent pick up?</span>
          <select
            className="input"
            value={config.pickup_mode}
            onChange={(e) => setConfig({ ...config, pickup_mode: e.target.value as PickupMode })}
          >
            <option value="ALWAYS">Always — the agent answers every call directly</option>
            <option value="AFTER_HOURS">After hours only — forwards to your line otherwise</option>
            <option value="NO_ANSWER">If unanswered — rings your line first</option>
          </select>
        </label>

        {config.pickup_mode === "AFTER_HOURS" && (
          <div className="row" style={{ flexWrap: "wrap" }}>
            <label className="stack" style={{ gap: 4 }}>
              <span style={{ fontSize: 13, color: "var(--color-text-muted)" }}>After-hours start</span>
              <input
                className="input"
                type="time"
                value={config.after_hours_start?.slice(0, 5) ?? ""}
                onChange={(e) => setConfig({ ...config, after_hours_start: e.target.value ? `${e.target.value}:00` : null })}
              />
            </label>
            <label className="stack" style={{ gap: 4 }}>
              <span style={{ fontSize: 13, color: "var(--color-text-muted)" }}>Until</span>
              <input
                className="input"
                type="time"
                value={config.after_hours_end?.slice(0, 5) ?? ""}
                onChange={(e) => setConfig({ ...config, after_hours_end: e.target.value ? `${e.target.value}:00` : null })}
              />
            </label>
          </div>
        )}

        {config.pickup_mode === "NO_ANSWER" && (
          <label className="stack" style={{ gap: 4, maxWidth: 200 }}>
            <span style={{ fontSize: 13, color: "var(--color-text-muted)" }}>Pick up after (seconds)</span>
            <input
              className="input"
              type="number"
              min={1}
              max={60}
              value={config.no_answer_timeout_seconds}
              onChange={(e) => setConfig({ ...config, no_answer_timeout_seconds: Number(e.target.value) })}
            />
          </label>
        )}

        {(config.pickup_mode === "AFTER_HOURS" || config.pickup_mode === "NO_ANSWER") && (
          <label className="stack" style={{ gap: 4, maxWidth: 240 }}>
            <span style={{ fontSize: 13, color: "var(--color-text-muted)" }}>Clinic's real line (forwards to)</span>
            <input
              className="input"
              placeholder="+1 555 010 0100"
              value={config.forward_to_number ?? ""}
              onChange={(e) => setConfig({ ...config, forward_to_number: e.target.value || null })}
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
        <span style={{ fontSize: 13, color: "var(--color-text-muted)" }}>
          Also converses in (for expat patients):
        </span>
        <div className="row" style={{ flexWrap: "wrap", gap: 8 }}>
          {EU_LANGUAGES.filter((l) => l.code !== config.default_language).map((l) => (
            <label key={l.code} className="row" style={{ gap: 4, fontSize: 13 }}>
              <input type="checkbox" checked={config.additional_languages.includes(l.code)} onChange={() => toggleLanguage(l.code)} />
              {l.label}
            </label>
          ))}
        </div>
      </div>

      <div className="card stack">
        <strong>Greeting</strong>
        <textarea
          className="input"
          rows={2}
          value={config.greeting_text}
          onChange={(e) => setConfig({ ...config, greeting_text: e.target.value })}
        />
      </div>

      <div className="card stack">
        <strong>Recording &amp; summaries</strong>
        <label className="row" style={{ gap: 8 }}>
          <input type="checkbox" checked={config.recording_enabled} onChange={(e) => setConfig({ ...config, recording_enabled: e.target.checked })} />
          Record every call
        </label>
        <div className="row" style={{ flexWrap: "wrap" }}>
          <label className="stack" style={{ gap: 4 }}>
            <span style={{ fontSize: 13, color: "var(--color-text-muted)" }}>Share call summaries with</span>
            <select
              className="input"
              value={config.share_summary_with}
              onChange={(e) => setConfig({ ...config, share_summary_with: e.target.value as SummaryShareWith })}
            >
              <option value="DOCTOR_ONLY">The doctor only</option>
              <option value="TEAM">The whole team</option>
            </select>
          </label>
          <label className="stack" style={{ gap: 4 }}>
            <span style={{ fontSize: 13, color: "var(--color-text-muted)" }}>Via</span>
            <select
              className="input"
              value={config.share_channel}
              onChange={(e) => setConfig({ ...config, share_channel: e.target.value as ContactChannel })}
            >
              <option value="EMAIL">Email</option>
              <option value="WHATSAPP">WhatsApp</option>
              <option value="SMS">SMS</option>
            </select>
          </label>
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
