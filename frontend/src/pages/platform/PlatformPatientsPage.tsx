import { useEffect, useState } from "react";
import * as platformApi from "../../api/platform";
import { ApiError } from "../../api/client";
import type { Clinic, Patient } from "../../types";

/** Cross-clinic patient browsing — one clinic at a time (see
 * list_clinic_patients on the backend: a platform admin drills into a
 * clinic rather than a single giant cross-tenant query). */
export function PlatformPatientsPage() {
  const [clinics, setClinics] = useState<Clinic[]>([]);
  const [clinicId, setClinicId] = useState("");
  const [patients, setPatients] = useState<Patient[]>([]);
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
      .listClinicPatients(clinicId)
      .then(setPatients)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load patients"));
  }, [clinicId]);

  if (loading) return <div className="page">Loading…</div>;

  return (
    <div className="stack">
      <h1 style={{ fontSize: 22 }}>Patients</h1>

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
                  <th>Name</th>
                  <th>Date of birth</th>
                  <th>MRN</th>
                  <th>Phone</th>
                  <th>Email</th>
                </tr>
              </thead>
              <tbody>
                {patients.map((p) => (
                  <tr key={p.id}>
                    <td>
                      {p.first_name} {p.last_name}
                    </td>
                    <td>{p.date_of_birth}</td>
                    <td>{p.mrn ?? "—"}</td>
                    <td>{p.phone ?? "—"}</td>
                    <td>{p.email ?? "—"}</td>
                  </tr>
                ))}
                {patients.length === 0 && (
                  <tr>
                    <td colSpan={5} style={{ color: "var(--color-text-muted)" }}>
                      No patients yet for this clinic.
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
