import { useEffect, useState } from "react";
import * as platformApi from "../../api/platform";
import { ApiError } from "../../api/client";
import type { Clinic } from "../../types";

/** A specific clinic's own name/contact info/email settings — separate
 * from whichever clinic the logged-in platform admin's own account
 * belongs to. Each clinic keeps its own contact_email/staff_email row;
 * this is just the first screen that lets a platform admin edit them for
 * clinics other than their own (previously only possible via a doctor's
 * own /settings page, which only ever acts on their own clinic). */
export function ClinicDetailsTab({ clinic, onUpdated }: { clinic: Clinic; onUpdated: (c: Clinic) => void }) {
  const [name, setName] = useState(clinic.name);
  const [address, setAddress] = useState(clinic.address ?? "");
  const [phone, setPhone] = useState(clinic.phone ?? "");
  const [contactEmail, setContactEmail] = useState(clinic.contact_email ?? "");
  const [staffEmail, setStaffEmail] = useState(clinic.staff_email ?? "");
  const [brandingName, setBrandingName] = useState(clinic.branding_name ?? "");
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [logoBusy, setLogoBusy] = useState(false);
  const [logoError, setLogoError] = useState<string | null>(null);

  useEffect(() => {
    setName(clinic.name);
    setAddress(clinic.address ?? "");
    setPhone(clinic.phone ?? "");
    setContactEmail(clinic.contact_email ?? "");
    setStaffEmail(clinic.staff_email ?? "");
    setBrandingName(clinic.branding_name ?? "");
    setSaved(null);
    setError(null);
    setLogoError(null);
  }, [clinic.id]); // eslint-disable-line react-hooks/exhaustive-deps

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    setSaved(null);
    try {
      const updated = await platformApi.updateClinic(clinic.id, {
        name: name.trim(),
        address: address.trim() || undefined,
        phone: phone.trim() || undefined,
        contact_email: contactEmail.trim() || undefined,
        staff_email: staffEmail.trim() || undefined,
        branding_name: brandingName.trim() || null,
      });
      onUpdated(updated);
      setSaved("Saved.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to save clinic details");
    } finally {
      setSaving(false);
    }
  }

  async function handleLogoChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setLogoBusy(true);
    setLogoError(null);
    try {
      const updated = await platformApi.uploadClinicLogo(clinic.id, file);
      onUpdated(updated);
    } catch (err) {
      setLogoError(err instanceof ApiError ? err.message : "Failed to upload logo");
    } finally {
      setLogoBusy(false);
      e.target.value = "";
    }
  }

  async function handleRemoveLogo() {
    setLogoBusy(true);
    setLogoError(null);
    try {
      const updated = await platformApi.deleteClinicLogo(clinic.id);
      onUpdated(updated);
    } catch (err) {
      setLogoError(err instanceof ApiError ? err.message : "Failed to remove logo");
    } finally {
      setLogoBusy(false);
    }
  }

  return (
    <form className="stack" onSubmit={handleSave}>
      <div className="card stack">
        <strong>Clinic details</strong>
        <label className="stack" style={{ gap: 4, maxWidth: 420 }}>
          <span style={{ fontSize: 13, color: "var(--color-text-muted)" }}>Name</span>
          <input className="input" value={name} onChange={(e) => setName(e.target.value)} required />
        </label>
        <label className="stack" style={{ gap: 4, maxWidth: 420 }}>
          <span style={{ fontSize: 13, color: "var(--color-text-muted)" }}>Address</span>
          <input className="input" value={address} onChange={(e) => setAddress(e.target.value)} />
        </label>
        <label className="stack" style={{ gap: 4, maxWidth: 420 }}>
          <span style={{ fontSize: 13, color: "var(--color-text-muted)" }}>Phone</span>
          <input className="input" value={phone} onChange={(e) => setPhone(e.target.value)} />
        </label>
      </div>

      <div className="card stack">
        <strong>Email</strong>
        <p style={{ margin: 0, fontSize: 13, color: "var(--color-text-muted)" }}>
          This clinic's own settings — editing here affects only <strong>{clinic.name}</strong>, never
          any other clinic.
        </p>
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
        </label>
      </div>

      <div className="card stack">
        <strong>Branding (white-label)</strong>
        <p style={{ margin: 0, fontSize: 13, color: "var(--color-text-muted)" }}>
          Platform-admin only — replaces the default MedicDesk.ai logo and wordmark with this
          clinic's own, everywhere its doctors see it. Leave blank to keep the default MedicDesk.ai
          branding.
        </p>
        <label className="stack" style={{ gap: 4, maxWidth: 420 }}>
          <span style={{ fontSize: 13, color: "var(--color-text-muted)" }}>Wordmark text</span>
          <input
            className="input"
            placeholder="MedicDesk.ai"
            value={brandingName}
            onChange={(e) => setBrandingName(e.target.value)}
          />
        </label>

        <div className="row" style={{ gap: 12, alignItems: "center" }}>
          <div
            style={{
              width: 40,
              height: 40,
              borderRadius: "50%",
              overflow: "hidden",
              flexShrink: 0,
              background: "var(--color-surface-hover)",
              border: "1px solid var(--color-border)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            {clinic.logo_url ? (
              <img src={clinic.logo_url} alt="Clinic logo" style={{ width: "100%", height: "100%", objectFit: "cover" }} />
            ) : (
              <span style={{ fontSize: 11, color: "var(--color-text-muted)" }}>None</span>
            )}
          </div>
          <label className="btn" style={{ cursor: logoBusy ? "wait" : "pointer" }}>
            {logoBusy ? "Working…" : clinic.logo_url ? "Replace logo" : "Upload logo"}
            <input type="file" accept="image/*" onChange={handleLogoChange} disabled={logoBusy} style={{ display: "none" }} />
          </label>
          {clinic.logo_url && (
            <button type="button" className="btn" onClick={handleRemoveLogo} disabled={logoBusy}>
              Remove logo
            </button>
          )}
        </div>
        {logoError && <div className="error-text">{logoError}</div>}
      </div>

      {error && <div className="error-text">{error}</div>}

      <div className="row">
        <button className="btn btn-primary" type="submit" disabled={saving}>
          {saving ? "Saving…" : "Save"}
        </button>
        {saved && <span style={{ fontSize: 13, color: "var(--color-text-muted)" }}>{saved}</span>}
      </div>
    </form>
  );
}
