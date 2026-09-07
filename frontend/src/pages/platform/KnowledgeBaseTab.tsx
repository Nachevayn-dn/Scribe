import { useEffect, useState } from "react";
import * as agentContentApi from "../../api/agentContent";
import { ApiError } from "../../api/client";
import type { AgentKnowledgeDocument, AgentType, Clinic } from "../../types";

const AGENT_TYPE_LABELS: Record<AgentType, string> = {
  INBOUND: "Inbound agent",
  OUTBOUND: "Outbound agent",
};

/** The reference-material repository — services/prices/Q&A/procedure and
 * decision-tree documents the inbound agent draws on, and pre-procedure
 * instructions for the outbound agent. Any file type; text is pulled out
 * automatically so it's ready for the agent's prompts. */
export function KnowledgeBaseTab({ clinic }: { clinic: Clinic }) {
  const [documents, setDocuments] = useState<AgentKnowledgeDocument[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [agentType, setAgentType] = useState<AgentType>("INBOUND");
  const [title, setTitle] = useState("");
  const [uploading, setUploading] = useState(false);

  async function refresh() {
    setLoading(true);
    try {
      setDocuments(await agentContentApi.listKnowledgeDocuments(clinic.id));
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
    if (!title.trim()) {
      setError("Give the document a title first");
      return;
    }
    setUploading(true);
    setError(null);
    try {
      await agentContentApi.uploadKnowledgeDocument(clinic.id, agentType, title.trim(), file);
      setTitle("");
      await refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to upload document");
    } finally {
      setUploading(false);
    }
  }

  async function handleDownload(doc: AgentKnowledgeDocument) {
    try {
      await agentContentApi.downloadKnowledgeDocument(clinic.id, doc.id, doc.original_filename);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to download document");
    }
  }

  async function handleRetire(doc: AgentKnowledgeDocument) {
    try {
      await agentContentApi.retireKnowledgeDocument(clinic.id, doc.id);
      await refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to retire document");
    }
  }

  if (loading) return <div className="card">Loading…</div>;

  return (
    <div className="stack">
      <div className="card stack">
        <strong>Upload a document</strong>
        <p style={{ margin: 0, fontSize: 13, color: "var(--color-text-muted)" }}>
          Services &amp; pricing, a doctor Q&amp;A, procedure decision trees, pre-op instructions — any
          file format. Text is pulled out automatically for the agent to use.
        </p>
        <div className="row" style={{ flexWrap: "wrap" }}>
          <select className="input" value={agentType} onChange={(e) => setAgentType(e.target.value as AgentType)} style={{ width: 180 }}>
            <option value="INBOUND">Inbound agent</option>
            <option value="OUTBOUND">Outbound agent</option>
          </select>
          <input
            className="input"
            placeholder="Title, e.g. Services & Pricing"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            style={{ width: 260 }}
          />
          <label className="btn btn-primary" style={{ cursor: "pointer" }}>
            {uploading ? "Uploading…" : "Upload file"}
            <input
              type="file"
              accept="application/pdf,.docx,text/plain,text/markdown,text/csv,image/png,image/jpeg"
              onChange={handleUpload}
              disabled={uploading}
              style={{ display: "none" }}
            />
          </label>
        </div>
      </div>

      {error && <div className="error-text">{error}</div>}

      <div className="card">
        <table>
          <thead>
            <tr>
              <th>Agent</th>
              <th>Title</th>
              <th>File</th>
              <th>Status</th>
              <th>Uploaded</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {documents.map((d) => (
              <tr key={d.id}>
                <td>
                  <span className="badge">{AGENT_TYPE_LABELS[d.agent_type]}</span>
                </td>
                <td>{d.title}</td>
                <td>
                  {d.original_filename}
                  {!d.has_extracted_text && (
                    <span style={{ fontSize: 11, color: "var(--color-text-muted)" }} title="No text could be pulled from this file automatically">
                      {" "}
                      (no text extracted)
                    </span>
                  )}
                </td>
                <td>{d.is_active ? "Active" : "Retired"}</td>
                <td>{new Date(d.created_at).toLocaleDateString()}</td>
                <td>
                  <div className="row">
                    <button className="btn" onClick={() => handleDownload(d)}>
                      Download
                    </button>
                    {d.is_active && (
                      <button className="btn" onClick={() => handleRetire(d)}>
                        Retire
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
            {documents.length === 0 && (
              <tr>
                <td colSpan={6} style={{ color: "var(--color-text-muted)" }}>
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
