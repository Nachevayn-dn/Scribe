import { useEffect, useState } from "react";
import * as platformApi from "../../api/platform";
import { ApiError } from "../../api/client";
import { SettingsPage } from "../SettingsPage";
import { ClinicDetailsTab } from "./ClinicDetailsTab";
import { DecisionRulesTab } from "./DecisionRulesTab";
import { KnowledgeBaseTab } from "./KnowledgeBaseTab";
import { OutboundSettingsTab } from "./OutboundSettingsTab";
import { TelephonyTab } from "./TelephonyTab";
import type { Announcement, Clinic, ClinicDocument, ClinicDocumentType, User, UserRole } from "../../types";

type Tab = "clinics" | "details" | "team" | "telephony" | "outbound" | "knowledge" | "rules" | "documents" | "announcements" | "myAccount";

const TAB_LABELS: Record<Tab, string> = {
  clinics: "Clinics",
  details: "Details",
  team: "Team",
  telephony: "Telephony",
  outbound: "Outbound agent",
  knowledge: "Knowledge base",
  rules: "Decision rules",
  documents: "Documents",
  announcements: "Announcements",
  myAccount: "My Account",
};

const DOC_TYPE_LABELS: Record<ClinicDocumentType, string> = {
  CONTRACT: "Signed contract",
  ORDER_FORM: "Order form",
  CONSENT_FORM: "Consent form",
};

/** The onboarding workspace: create a clinic, add its doctors before any
 * login exists, attach the contract/order form, upload consent forms, then
 * generate credentials once the clinic's ready to go live. */
export function PlatformSettingsPage() {
  const [tab, setTab] = useState<Tab>("clinics");
  const [clinics, setClinics] = useState<Clinic[]>([]);
  const [selectedClinicId, setSelectedClinicId] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function refreshClinics() {
    try {
      const cs = await platformApi.listClinics();
      setClinics(cs);
      if (!selectedClinicId && cs.length > 0) setSelectedClinicId(cs[0].id);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load clinics");
    }
  }

  useEffect(() => {
    refreshClinics();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const selectedClinic = clinics.find((c) => c.id === selectedClinicId) ?? null;

  return (
    <div className="stack">
      <h1 style={{ fontSize: 22 }}>Settings</h1>

      <div className="row" style={{ flexWrap: "wrap" }}>
        {(["clinics", "details", "team", "telephony", "outbound", "knowledge", "rules", "documents", "announcements", "myAccount"] as Tab[]).map((t) => (
          <button
            key={t}
            className="btn"
            style={tab === t ? { borderColor: "var(--color-primary)", color: "var(--color-primary)" } : undefined}
            onClick={() => setTab(t)}
          >
            {TAB_LABELS[t]}
          </button>
        ))}
      </div>

      {error && <div className="error-text">{error}</div>}

      {tab === "clinics" && (
        <ClinicsTab
          clinics={clinics}
          onCreated={refreshClinics}
          onOpenClinic={(clinicId) => {
            setSelectedClinicId(clinicId);
            setTab("details");
          }}
        />
      )}

      {tab !== "clinics" && tab !== "myAccount" && tab !== "announcements" && (
        <label className="row" style={{ gap: 8 }}>
          <span style={{ fontSize: 13, color: "var(--color-text-muted)" }}>Clinic</span>
          <select
            className="input"
            style={{ width: 280 }}
            value={selectedClinicId}
            onChange={(e) => setSelectedClinicId(e.target.value)}
          >
            {clinics.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
        </label>
      )}

      {tab === "details" && selectedClinic && (
        <ClinicDetailsTab
          clinic={selectedClinic}
          onUpdated={(updated) => setClinics((prev) => prev.map((c) => (c.id === updated.id ? updated : c)))}
        />
      )}
      {tab === "team" && selectedClinic && <TeamTab clinic={selectedClinic} />}
      {tab === "telephony" && selectedClinic && <TelephonyTab clinic={selectedClinic} />}
      {tab === "outbound" && selectedClinic && <OutboundSettingsTab clinic={selectedClinic} />}
      {tab === "knowledge" && selectedClinic && <KnowledgeBaseTab clinic={selectedClinic} />}
      {tab === "rules" && selectedClinic && <DecisionRulesTab clinic={selectedClinic} />}
      {tab === "documents" && selectedClinic && <DocumentsTab clinic={selectedClinic} />}
      {tab === "announcements" && <AnnouncementsTab clinics={clinics} />}
      {tab === "myAccount" && <SettingsPage />}
    </div>
  );
}

function ClinicsTab({
  clinics,
  onCreated,
  onOpenClinic,
}: {
  clinics: Clinic[];
  onCreated: () => void;
  onOpenClinic: (clinicId: string) => void;
}) {
  const [name, setName] = useState("");
  const [address, setAddress] = useState("");
  const [phone, setPhone] = useState("");
  const [doctorName, setDoctorName] = useState("");
  const [doctorEmail, setDoctorEmail] = useState("");
  const [doctorRole, setDoctorRole] = useState<Extract<UserRole, "PROVIDER" | "ASSISTANT">>("PROVIDER");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [revealed, setRevealed] = useState<
    { clinicName: string; doctorEmail: string; setup_url: string; emailed: boolean; email_error: string | null } | null
  >(null);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    setSaving(true);
    setError(null);
    setRevealed(null);
    try {
      const clinic = await platformApi.createClinic({
        name: name.trim(),
        address: address.trim() || undefined,
        phone: phone.trim() || undefined,
      });

      // Onboarding a clinic without a doctor yet is still valid (e.g.
      // attaching contracts first) — only provision + send a link when
      // both doctor fields are filled in.
      if (doctorName.trim() && doctorEmail.trim()) {
        const doctor = await platformApi.provisionDoctor(clinic.id, {
          email: doctorEmail.trim(),
          full_name: doctorName.trim(),
          role: doctorRole,
        });
        const link = await platformApi.sendSetupLink(doctor.id, true);
        setRevealed({ clinicName: clinic.name, doctorEmail: doctor.email, ...link });
        setCopied(false);
      }

      setName("");
      setAddress("");
      setPhone("");
      setDoctorName("");
      setDoctorEmail("");
      setDoctorRole("PROVIDER");
      onCreated();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to create clinic and doctor");
    } finally {
      setSaving(false);
    }
  }

  async function handleCopyLink() {
    if (!revealed) return;
    try {
      await navigator.clipboard.writeText(revealed.setup_url);
      setCopied(true);
    } catch {
      setError("Couldn't copy — select and copy the link manually");
    }
  }

  return (
    <div className="stack">
      <form className="card stack" onSubmit={handleCreate}>
        <strong style={{ fontSize: 13 }}>New clinic</strong>
        <div className="row" style={{ flexWrap: "wrap" }}>
          <input className="input" placeholder="Clinic name" value={name} onChange={(e) => setName(e.target.value)} style={{ width: 220 }} required />
          <input className="input" placeholder="Address (optional)" value={address} onChange={(e) => setAddress(e.target.value)} style={{ width: 220 }} />
          <input className="input" placeholder="Phone (optional)" value={phone} onChange={(e) => setPhone(e.target.value)} style={{ width: 160 }} />
        </div>
        <strong style={{ fontSize: 13 }}>First doctor (optional — leave blank to just create the clinic)</strong>
        <div className="row" style={{ flexWrap: "wrap" }}>
          <input className="input" placeholder="Doctor's full name" value={doctorName} onChange={(e) => setDoctorName(e.target.value)} style={{ width: 200 }} />
          <input className="input" type="email" placeholder="Doctor's email" value={doctorEmail} onChange={(e) => setDoctorEmail(e.target.value)} style={{ width: 220 }} />
          <select className="input" value={doctorRole} onChange={(e) => setDoctorRole(e.target.value as typeof doctorRole)} style={{ width: 160 }}>
            <option value="PROVIDER">Provider (doctor)</option>
            <option value="ASSISTANT">Assistant</option>
          </select>
        </div>
        <div className="row" style={{ justifyContent: "flex-end" }}>
          <button className="btn btn-primary" type="submit" disabled={saving}>
            {saving ? "Creating…" : doctorName.trim() && doctorEmail.trim() ? "+ New clinic & send setup link" : "+ New clinic"}
          </button>
        </div>
      </form>

      {error && <div className="error-text">{error}</div>}

      {revealed && (
        <div className="card stack" style={{ borderColor: "var(--color-primary)" }}>
          <strong>
            {revealed.clinicName} created — setup link for {revealed.doctorEmail}
          </strong>
          <p style={{ margin: 0, fontFamily: "monospace", fontSize: 13, wordBreak: "break-all" }}>
            {revealed.setup_url}
          </p>
          <p style={{ margin: 0, fontSize: 12, color: "var(--color-text-muted)" }}>
            Valid for 7 days.{" "}
            {revealed.emailed ? "Emailed to them." : revealed.email_error ? `Not emailed: ${revealed.email_error} — share the link another way.` : ""}
          </p>
          <div className="row" style={{ justifyContent: "flex-end" }}>
            <button className="btn" onClick={handleCopyLink}>
              {copied ? "Copied ✓" : "Copy link"}
            </button>
            <button className="btn" onClick={() => setRevealed(null)}>
              Done
            </button>
          </div>
        </div>
      )}

      <div className="card">
        <table>
          <thead>
            <tr>
              <th>Name</th>
              <th>Address</th>
              <th>Phone</th>
            </tr>
          </thead>
          <tbody>
            {clinics.map((c) => (
              <tr key={c.id}>
                <td>
                  <button
                    style={{
                      background: "none",
                      border: "none",
                      padding: 0,
                      color: "var(--color-primary)",
                      cursor: "pointer",
                      font: "inherit",
                      textDecoration: "underline",
                    }}
                    onClick={() => onOpenClinic(c.id)}
                  >
                    {c.name}
                  </button>
                </td>
                <td>{c.address ?? "—"}</td>
                <td>{c.phone ?? "—"}</td>
              </tr>
            ))}
            {clinics.length === 0 && (
              <tr>
                <td colSpan={3} style={{ color: "var(--color-text-muted)" }}>
                  No clinics yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function TeamTab({ clinic }: { clinic: Clinic }) {
  const [doctors, setDoctors] = useState<User[]>([]);
  const [documents, setDocuments] = useState<ClinicDocument[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [email, setEmail] = useState("");
  const [fullName, setFullName] = useState("");
  const [role, setRole] = useState<Extract<UserRole, "PROVIDER" | "ASSISTANT">>("PROVIDER");
  const [saving, setSaving] = useState(false);

  const [generatingFor, setGeneratingFor] = useState<string | null>(null);
  const [sendEmailChecked, setSendEmailChecked] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [revealed, setRevealed] = useState<
    { email: string; setup_url: string; emailed: boolean; email_error: string | null } | null
  >(null);
  const [copied, setCopied] = useState(false);
  const [retentionSaving, setRetentionSaving] = useState<string | null>(null);

  async function refresh() {
    setLoading(true);
    try {
      const [nextDoctors, nextDocuments] = await Promise.all([
        platformApi.listClinicDoctors(clinic.id),
        platformApi.listClinicDocuments(clinic.id),
      ]);
      setDoctors(nextDoctors);
      setDocuments(nextDocuments);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load team");
    } finally {
      setLoading(false);
    }
  }

  function hasSignedConsent(doctorId: string) {
    return documents.some((d) => d.provider_id === doctorId && d.doc_type === "CONSENT_FORM");
  }

  async function handleToggleRetention(doctor: User) {
    setRetentionSaving(doctor.id);
    setError(null);
    try {
      await platformApi.updateRetention(doctor.id, !doctor.retain_all_sessions);
      await refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to update retention");
    } finally {
      setRetentionSaving(null);
    }
  }

  useEffect(() => {
    refresh();
    setRevealed(null);
    setGeneratingFor(null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [clinic.id]);

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault();
    if (!email.trim() || !fullName.trim()) return;
    setSaving(true);
    setError(null);
    try {
      await platformApi.provisionDoctor(clinic.id, { email: email.trim(), full_name: fullName.trim(), role });
      setEmail("");
      setFullName("");
      await refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to add team member");
    } finally {
      setSaving(false);
    }
  }

  async function handleGenerate(user: User) {
    setGenerating(true);
    setError(null);
    try {
      const result = await platformApi.sendSetupLink(user.id, sendEmailChecked);
      setRevealed({ email: user.email, ...result });
      setCopied(false);
      setGeneratingFor(null);
      await refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to send setup link");
    } finally {
      setGenerating(false);
    }
  }

  async function handleCopyLink() {
    if (!revealed) return;
    try {
      await navigator.clipboard.writeText(revealed.setup_url);
      setCopied(true);
    } catch {
      setError("Couldn't copy — select and copy the link manually");
    }
  }

  if (loading) return <div className="card">Loading…</div>;

  return (
    <div className="stack">
      <form className="card row" onSubmit={handleAdd} style={{ flexWrap: "wrap" }}>
        <input className="input" placeholder="Full name" value={fullName} onChange={(e) => setFullName(e.target.value)} style={{ width: 200 }} required />
        <input className="input" type="email" placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)} style={{ width: 220 }} required />
        <select className="input" value={role} onChange={(e) => setRole(e.target.value as typeof role)} style={{ width: 160 }}>
          <option value="PROVIDER">Provider (doctor)</option>
          <option value="ASSISTANT">Assistant</option>
        </select>
        <button className="btn btn-primary" type="submit" disabled={saving}>
          {saving ? "Adding…" : "+ Add team member"}
        </button>
      </form>
      <p style={{ fontSize: 12, color: "var(--color-text-muted)", margin: "-4px 0 0" }}>
        Added with no password — send them a setup link below once the clinic's ready to go live;
        they pick their own password from it.
      </p>

      {error && <div className="error-text">{error}</div>}

      {revealed && (
        <div className="card stack" style={{ borderColor: "var(--color-primary)" }}>
          <strong>Setup link for {revealed.email}</strong>
          <p style={{ margin: 0, fontFamily: "monospace", fontSize: 13, wordBreak: "break-all" }}>
            {revealed.setup_url}
          </p>
          <p style={{ margin: 0, fontSize: 12, color: "var(--color-text-muted)" }}>
            Valid for 7 days.{" "}
            {revealed.emailed ? "Emailed to them." : revealed.email_error ? `Not emailed: ${revealed.email_error} — share the link another way.` : ""}
          </p>
          <div className="row" style={{ justifyContent: "flex-end" }}>
            <button className="btn" onClick={handleCopyLink}>
              {copied ? "Copied ✓" : "Copy link"}
            </button>
            <button className="btn" onClick={() => setRevealed(null)}>
              Done
            </button>
          </div>
        </div>
      )}

      <div className="card">
        <table>
          <thead>
            <tr>
              <th>Name</th>
              <th>Email</th>
              <th>Role</th>
              <th>Credentials</th>
              <th>Retention</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {doctors.map((d) => (
              <tr key={d.id}>
                <td>{d.full_name}</td>
                <td>{d.email}</td>
                <td>
                  <span className="badge">{d.role}</span>
                </td>
                <td>
                  {d.password_set_at ? (
                    <span style={{ fontSize: 13, color: "var(--color-text-muted)" }}>Set</span>
                  ) : (
                    <span className="badge" style={{ background: "var(--color-danger)", color: "#fff" }}>
                      Pending
                    </span>
                  )}
                </td>
                <td>
                  <div className="row" style={{ gap: 6, alignItems: "center" }}>
                    <span
                      className="badge"
                      title={d.retain_all_sessions ? "Sessions kept indefinitely" : "Sessions auto-delete after 14 days"}
                    >
                      {d.retain_all_sessions ? "Retains all" : "14-day auto-delete"}
                    </span>
                    <button
                      className="btn"
                      style={{ fontSize: 12, padding: "2px 8px" }}
                      disabled={retentionSaving === d.id || (!d.retain_all_sessions && !hasSignedConsent(d.id))}
                      title={
                        !d.retain_all_sessions && !hasSignedConsent(d.id)
                          ? "Upload a signed consent form for this doctor in the Documents tab first"
                          : undefined
                      }
                      onClick={() => handleToggleRetention(d)}
                    >
                      {retentionSaving === d.id ? "Saving…" : d.retain_all_sessions ? "Switch to 14-day" : "Enable retain-all"}
                    </button>
                  </div>
                </td>
                <td>
                  {generatingFor === d.id ? (
                    <div className="row">
                      <label className="row" style={{ gap: 4, fontSize: 12 }}>
                        <input type="checkbox" checked={sendEmailChecked} onChange={(e) => setSendEmailChecked(e.target.checked)} />
                        Email it
                      </label>
                      <button className="btn btn-primary" disabled={generating} onClick={() => handleGenerate(d)}>
                        {generating ? "Sending…" : "Send"}
                      </button>
                      <button className="btn" onClick={() => setGeneratingFor(null)}>
                        Cancel
                      </button>
                    </div>
                  ) : (
                    <button className="btn" onClick={() => setGeneratingFor(d.id)}>
                      {d.password_set_at ? "Resend setup link" : "Send setup link"}
                    </button>
                  )}
                </td>
              </tr>
            ))}
            {doctors.length === 0 && (
              <tr>
                <td colSpan={6} style={{ color: "var(--color-text-muted)" }}>
                  No team members yet for {clinic.name}.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function DocumentsTab({ clinic }: { clinic: Clinic }) {
  const [documents, setDocuments] = useState<ClinicDocument[]>([]);
  const [doctors, setDoctors] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [docType, setDocType] = useState<ClinicDocumentType>("CONTRACT");
  const [providerId, setProviderId] = useState<string>("");
  const [uploading, setUploading] = useState(false);

  async function refresh() {
    setLoading(true);
    try {
      const [nextDocuments, nextDoctors] = await Promise.all([
        platformApi.listClinicDocuments(clinic.id),
        platformApi.listClinicDoctors(clinic.id),
      ]);
      setDocuments(nextDocuments);
      setDoctors(nextDoctors);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load documents");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [clinic.id]);

  function doctorName(id: string | null) {
    if (!id) return "Clinic-wide";
    return doctors.find((d) => d.id === id)?.full_name ?? "Former team member";
  }

  async function handleUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    setUploading(true);
    setError(null);
    try {
      await platformApi.uploadClinicDocument(clinic.id, docType, file, providerId || undefined);
      await refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to upload document");
    } finally {
      setUploading(false);
    }
  }

  async function handleDownload(doc: ClinicDocument) {
    try {
      await platformApi.downloadClinicDocument(clinic.id, doc.id, doc.original_filename);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to download document");
    }
  }

  if (loading) return <div className="card">Loading…</div>;

  return (
    <div className="stack">
      <div className="card row" style={{ flexWrap: "wrap" }}>
        <select className="input" value={docType} onChange={(e) => setDocType(e.target.value as ClinicDocumentType)} style={{ width: 200 }}>
          <option value="CONTRACT">Signed contract</option>
          <option value="ORDER_FORM">Order form</option>
          <option value="CONSENT_FORM">Consent form</option>
        </select>
        <select className="input" value={providerId} onChange={(e) => setProviderId(e.target.value)} style={{ width: 200 }}>
          <option value="">Clinic-wide</option>
          {doctors.map((d) => (
            <option key={d.id} value={d.id}>
              For {d.full_name}
            </option>
          ))}
        </select>
        <label className="btn btn-primary" style={{ cursor: "pointer" }}>
          {uploading ? "Uploading…" : "Upload PDF"}
          <input type="file" accept="application/pdf,image/png,image/jpeg" onChange={handleUpload} disabled={uploading} style={{ display: "none" }} />
        </label>
        <span style={{ fontSize: 12, color: "var(--color-text-muted)" }}>English only, for now.</span>
      </div>
      <p style={{ fontSize: 12, color: "var(--color-text-muted)", margin: "-4px 0 0" }}>
        A signed Consent form scoped to a specific doctor is what unlocks that doctor's "retain all
        sessions" toggle in the Team tab, instead of the platform's normal 14-day auto-delete.
      </p>

      {error && <div className="error-text">{error}</div>}

      <div className="card">
        <table>
          <thead>
            <tr>
              <th>Type</th>
              <th>For</th>
              <th>File</th>
              <th>Uploaded</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {documents.map((d) => (
              <tr key={d.id}>
                <td>{DOC_TYPE_LABELS[d.doc_type]}</td>
                <td>{doctorName(d.provider_id)}</td>
                <td>{d.original_filename}</td>
                <td>{new Date(d.created_at).toLocaleDateString()}</td>
                <td>
                  <button className="btn" onClick={() => handleDownload(d)}>
                    Download
                  </button>
                </td>
              </tr>
            ))}
            {documents.length === 0 && (
              <tr>
                <td colSpan={5} style={{ color: "var(--color-text-muted)" }}>
                  No documents uploaded yet for {clinic.name}.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function AnnouncementsTab({ clinics }: { clinics: Clinic[] }) {
  const [announcements, setAnnouncements] = useState<Announcement[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [title, setTitle] = useState("");
  const [message, setMessage] = useState("");
  const [clinicId, setClinicId] = useState(""); // "" = all clinics
  const [video, setVideo] = useState<File | null>(null);
  const [sending, setSending] = useState(false);

  async function refresh() {
    setLoading(true);
    try {
      setAnnouncements(await platformApi.listAnnouncements());
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load announcements");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  async function handleSend(e: React.FormEvent) {
    e.preventDefault();
    if (!message.trim()) return;
    setSending(true);
    setError(null);
    try {
      await platformApi.createAnnouncement({
        message: message.trim(),
        title: title.trim() || undefined,
        clinicId: clinicId || undefined,
        video: video ?? undefined,
      });
      setTitle("");
      setMessage("");
      setClinicId("");
      setVideo(null);
      await refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to send announcement");
    } finally {
      setSending(false);
    }
  }

  async function handleRetire(a: Announcement) {
    if (!window.confirm("Retire this announcement? Anyone who hasn't seen it yet will stop being shown it.")) return;
    try {
      await platformApi.deactivateAnnouncement(a.id);
      await refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to retire announcement");
    }
  }

  function clinicName(id: string | null) {
    if (!id) return "Everyone";
    return clinics.find((c) => c.id === id)?.name ?? "Former clinic";
  }

  if (loading) return <div className="card">Loading…</div>;

  return (
    <div className="stack">
      <form className="card stack" onSubmit={handleSend}>
        <strong style={{ fontSize: 13 }}>New announcement</strong>
        <input
          className="input"
          placeholder="Title (optional)"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
        />
        <textarea
          className="input"
          placeholder="Message"
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          rows={4}
          required
        />
        <div className="row" style={{ flexWrap: "wrap" }}>
          <select className="input" value={clinicId} onChange={(e) => setClinicId(e.target.value)} style={{ width: 220 }}>
            <option value="">Send to everyone</option>
            {clinics.map((c) => (
              <option key={c.id} value={c.id}>
                Just {c.name}
              </option>
            ))}
          </select>
          <label className="btn" style={{ cursor: "pointer" }}>
            {video ? video.name : "Attach a video (optional)"}
            <input
              type="file"
              accept="video/mp4,video/webm,video/quicktime"
              onChange={(e) => setVideo(e.target.files?.[0] ?? null)}
              style={{ display: "none" }}
            />
          </label>
        </div>
        <div className="row" style={{ justifyContent: "flex-end" }}>
          <button className="btn btn-primary" type="submit" disabled={sending}>
            {sending ? "Sending…" : "Send announcement"}
          </button>
        </div>
      </form>
      <p style={{ fontSize: 12, color: "var(--color-text-muted)", margin: "-8px 0 0" }}>
        Shown as a popup the doctor must acknowledge ("Got it") before it goes away.
      </p>

      {error && <div className="error-text">{error}</div>}

      <div className="card">
        <table>
          <thead>
            <tr>
              <th>Sent to</th>
              <th>Title</th>
              <th>Message</th>
              <th>Video</th>
              <th>Status</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {announcements.map((a) => (
              <tr key={a.id}>
                <td>{clinicName(a.clinic_id)}</td>
                <td>{a.title ?? "—"}</td>
                <td style={{ maxWidth: 320, whiteSpace: "pre-wrap" }}>{a.message}</td>
                <td>{a.has_video ? "Yes" : "—"}</td>
                <td>
                  <span className="badge">{a.is_active ? "Active" : "Retired"}</span>
                </td>
                <td>
                  {a.is_active && (
                    <button className="btn" onClick={() => handleRetire(a)}>
                      Retire
                    </button>
                  )}
                </td>
              </tr>
            ))}
            {announcements.length === 0 && (
              <tr>
                <td colSpan={6} style={{ color: "var(--color-text-muted)" }}>
                  No announcements sent yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
