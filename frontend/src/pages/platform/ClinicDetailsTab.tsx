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
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setName(clinic.name);
    setAddress(clinic.address ?? "");
    setPhone(clinic.phone ?? "");
    setContactEmail(clinic.contact_email ?? "");
    setStaffEmail(clinic.staff_email ?? "");
    setSaved(null);
    setError(null);
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
      });
      onUpdated(updated);
      setSaved("Saved.");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to save clinic details");
    } finally {
      setSaving(false);
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
