import { useEffect, useState } from "react";
import * as platformApi from "../../api/platform";
import { ApiError } from "../../api/client";
import { IntegrationsPage } from "../IntegrationsPage";
import type { Clinic, ClinicDocument, ClinicDocumentType, User, UserRole } from "../../types";

type Tab = "clinics" | "team" | "documents" | "integrations";

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
        {(["clinics", "team", "documents", "integrations"] as Tab[]).map((t) => (
          <button
            key={t}
            className="btn"
            style={tab === t ? { borderColor: "var(--color-primary)", color: "var(--color-primary)" } : undefined}
            onClick={() => setTab(t)}
          >
            {t === "clinics" ? "Clinics" : t === "team" ? "Team" : t === "documents" ? "Documents" : "Integrations"}
          </button>
        ))}
      </div>

      {error && <div className="error-text">{error}</div>}

      {tab === "clinics" && <ClinicsTab clinics={clinics} onCreated={refreshClinics} />}

      {tab !== "clinics" && tab !== "integrations" && (
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

      {tab === "team" && selectedClinic && <TeamTab clinic={selectedClinic} />}
      {tab === "documents" && selectedClinic && <DocumentsTab clinic={selectedClinic} />}
      {tab === "integrations" && <IntegrationsPage />}
    </div>
  );
}

function ClinicsTab({ clinics, onCreated }: { clinics: Clinic[]; onCreated: () => void }) {
  const [name, setName] = useState("");
  const [address, setAddress] = useState("");
  const [phone, setPhone] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    setSaving(true);
    setError(null);
    try {
      await platformApi.createClinic({
        name: name.trim(),
        address: address.trim() || undefined,
        phone: phone.trim() || undefined,
      });
      setName("");
      setAddress("");
      setPhone("");
      onCreated();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to create clinic");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="stack">
      <form className="card row" onSubmit={handleCreate} style={{ flexWrap: "wrap" }}>
        <input className="input" placeholder="Clinic name" value={name} onChange={(e) => setName(e.target.value)} style={{ width: 220 }} required />
        <input className="input" placeholder="Address (optional)" value={address} onChange={(e) => setAddress(e.target.value)} style={{ width: 220 }} />
        <input className="input" placeholder="Phone (optional)" value={phone} onChange={(e) => setPhone(e.target.value)} style={{ width: 160 }} />
        <button className="btn btn-primary" type="submit" disabled={saving}>
          {saving ? "Creating…" : "+ New clinic"}
        </button>
      </form>

      {error && <div className="error-text">{error}</div>}

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
                <td>{c.name}</td>
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
    { email: string; temp_password: string; emailed: boolean; email_error: string | null } | null
  >(null);

  async function refresh() {
    setLoading(true);
    try {
      setDoctors(await platformApi.listClinicDoctors(clinic.id));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load team");
    } finally {
      setLoading(false);
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
      const result = await platformApi.generateCredentials(user.id, sendEmailChecked);
      setRevealed({ email: user.email, ...result });
      setGeneratingFor(null);
      await refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to generate credentials");
    } finally {
      setGenerating(false);
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
        Added with no password — generate credentials below once the clinic's ready to go live.
      </p>

      {error && <div className="error-text">{error}</div>}

      {revealed && (
        <div className="card stack" style={{ borderColor: "var(--color-primary)" }}>
          <strong>Credentials for {revealed.email}</strong>
          <p style={{ margin: 0, fontFamily: "monospace", fontSize: 15 }}>{revealed.temp_password}</p>
          <p style={{ margin: 0, fontSize: 12, color: "var(--color-text-muted)" }}>
            Shown once — copy it now. {revealed.emailed ? "Also emailed to them." : revealed.email_error ? `Not emailed: ${revealed.email_error}` : ""}
          </p>
          <div className="row" style={{ justifyContent: "flex-end" }}>
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
                    <span style={{ fontSize: 13, color: "var(--color-text-muted)" }}>Generated</span>
                  ) : (
                    <span className="badge" style={{ background: "var(--color-danger)", color: "#fff" }}>
                      Pending
                    </span>
                  )}
                </td>
                <td>
                  {!d.password_set_at &&
                    (generatingFor === d.id ? (
                      <div className="row">
                        <label className="row" style={{ gap: 4, fontSize: 12 }}>
                          <input type="checkbox" checked={sendEmailChecked} onChange={(e) => setSendEmailChecked(e.target.checked)} />
                          Email it
                        </label>
                        <button className="btn btn-primary" disabled={generating} onClick={() => handleGenerate(d)}>
                          {generating ? "Generating…" : "Generate"}
                        </button>
                        <button className="btn" onClick={() => setGeneratingFor(null)}>
                          Cancel
                        </button>
                      </div>
                    ) : (
                      <button className="btn" onClick={() => setGeneratingFor(d.id)}>
                        Generate credentials
                      </button>
                    ))}
                </td>
              </tr>
            ))}
            {doctors.length === 0 && (
              <tr>
                <td colSpan={5} style={{ color: "var(--color-text-muted)" }}>
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
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [docType, setDocType] = useState<ClinicDocumentType>("CONTRACT");
  const [uploading, setUploading] = useState(false);

  async function refresh() {
    setLoading(true);
    try {
      setDocuments(await platformApi.listClinicDocuments(clinic.id));
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

  async function handleUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    setUploading(true);
    setError(null);
    try {
      await platformApi.uploadClinicDocument(clinic.id, docType, file);
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
        <label className="btn btn-primary" style={{ cursor: "pointer" }}>
          {uploading ? "Uploading…" : "Upload PDF"}
          <input type="file" accept="application/pdf,image/png,image/jpeg" onChange={handleUpload} disabled={uploading} style={{ display: "none" }} />
        </label>
        <span style={{ fontSize: 12, color: "var(--color-text-muted)" }}>English only, for now.</span>
      </div>

      {error && <div className="error-text">{error}</div>}

      <div className="card">
        <table>
          <thead>
            <tr>
              <th>Type</th>
              <th>File</th>
              <th>Uploaded</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {documents.map((d) => (
              <tr key={d.id}>
                <td>{DOC_TYPE_LABELS[d.doc_type]}</td>
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
                <td colSpan={4} style={{ color: "var(--color-text-muted)" }}>
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
