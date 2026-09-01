import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import * as encountersApi from "../api/encounters";
import * as patientsApi from "../api/patients";
import type { Encounter, Patient } from "../types";

const STATUS_COLORS: Record<string, string> = {
  IN_PROGRESS: "#eef2ff",
  TRANSCRIBING: "#fef8e1",
  EXTRACTING: "#fef8e1",
  NOTE_READY: "#e9f7ec",
  SIGNED: "#dcfce7",
  FAILED: "#fdecec",
};

export function ProviderDashboard() {
  const [encounters, setEncounters] = useState<Encounter[]>([]);
  const [patientsById, setPatientsById] = useState<Record<string, Patient>>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      const list = await encountersApi.listEncounters();
      setEncounters(list);
      const patients = await patientsApi.listPatients();
      setPatientsById(Object.fromEntries(patients.map((p) => [p.id, p])));
      setLoading(false);
    })();
  }, []);

  if (loading) return <div className="page">Loading…</div>;

  return (
    <div className="page stack">
      <div className="row" style={{ justifyContent: "space-between" }}>
        <h1 style={{ fontSize: 22 }}>Encounters</h1>
        <Link className="btn btn-primary" to="/patients">
          + New encounter
        </Link>
      </div>

      <div className="card">
        <table>
          <thead>
            <tr>
              <th>Patient</th>
              <th>Started</th>
              <th>Status</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {encounters.map((e) => {
              const patient = patientsById[e.patient_id];
              return (
                <tr key={e.id}>
                  <td>{patient ? `${patient.first_name} ${patient.last_name}` : e.patient_id}</td>
                  <td>{new Date(e.started_at).toLocaleString()}</td>
                  <td>
                    <span className="badge" style={{ background: STATUS_COLORS[e.status] }}>
                      {e.status}
                    </span>
                  </td>
                  <td>
                    <Link className="btn" to={`/encounters/${e.id}`}>
                      Open
                    </Link>
                  </td>
                </tr>
              );
            })}
            {encounters.length === 0 && (
              <tr>
                <td colSpan={4} style={{ color: "var(--color-text-muted)" }}>
                  No encounters yet. Start one from the Patients page.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
