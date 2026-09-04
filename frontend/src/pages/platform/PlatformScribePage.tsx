import { useEffect, useState } from "react";
import * as platformApi from "../../api/platform";
import { ApiError } from "../../api/client";
import type { Clinic, Encounter } from "../../types";

const STATUS_LABELS: Record<string, string> = {
  IN_PROGRESS: "In progress",
  TRANSCRIBING: "Transcribing",
  TRANSCRIPT_READY: "Transcript ready",
  EXTRACTING: "Generating note",
  NOTE_READY: "Note ready",
  SIGNED: "Signed",
  FAILED: "Failed",
};

/** Cross-clinic Scribe session browsing — one clinic at a time, same
 * drill-down shape as PlatformPatientsPage. */
export function PlatformScribePage() {
  const [clinics, setClinics] = useState<Clinic[]>([]);
  const [clinicId, setClinicId] = useState("");
  const [encounters, setEncounters] = useState<Encounter[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    platformApi
      .listClinics()
      .then((cs) => {
        setClinics(cs);
        if (cs.length > 0) setClinicId(cs[0].id);
      })
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load clinics"))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!clinicId) return;
    platformApi
      .listClinicEncounters(clinicId)
      .then(setEncounters)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load sessions"));
  }, [clinicId]);

  if (loading) return <div className="page">Loading…</div>;

  return (
    <div className="stack">
      <h1 style={{ fontSize: 22 }}>Scribe</h1>

      {clinics.length === 0 ? (
        <div className="card" style={{ color: "var(--color-text-muted)" }}>
          No clinics yet — create one under Settings.
        </div>
      ) : (
        <>
          <label className="row" style={{ gap: 8 }}>
            <span style={{ fontSize: 13, color: "var(--color-text-muted)" }}>Clinic</span>
            <select className="input" style={{ width: 280 }} value={clinicId} onChange={(e) => setClinicId(e.target.value)}>
              {clinics.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          </label>

          {error && <div className="error-text">{error}</div>}

          <div className="card">
            <table>
              <thead>
                <tr>
                  <th>Started</th>
                  <th>Status</th>
                  <th>Language</th>
                </tr>
              </thead>
              <tbody>
                {encounters.map((e) => (
                  <tr key={e.id}>
                    <td>{new Date(e.started_at).toLocaleString()}</td>
                    <td>
                      <span className="badge">{STATUS_LABELS[e.status] ?? e.status}</span>
                    </td>
                    <td>{e.language ?? "auto"}</td>
                  </tr>
                ))}
                {encounters.length === 0 && (
                  <tr>
                    <td colSpan={3} style={{ color: "var(--color-text-muted)" }}>
                      No Scribe sessions yet for this clinic.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
