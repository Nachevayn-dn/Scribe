import { useEffect, useState } from "react";
import * as agentContentApi from "../../api/agentContent";
import * as platformApi from "../../api/platform";
import { ApiError } from "../../api/client";
import type { AgentDecisionRule, Clinic, User } from "../../types";

/** The inbound agent's "decision tree" — a modular, ordered list of
 * condition -> action rules. Clinic-wide by default; scoping a rule to one
 * doctor adds/overrides it just for their calls. */
export function DecisionRulesTab({ clinic }: { clinic: Clinic }) {
  const [rules, setRules] = useState<AgentDecisionRule[]>([]);
  const [doctors, setDoctors] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [condition, setCondition] = useState("");
  const [action, setAction] = useState("");
  const [priority, setPriority] = useState(0);
  const [providerId, setProviderId] = useState("");
  const [saving, setSaving] = useState(false);

  const [editingId, setEditingId] = useState<string | null>(null);
  const [editCondition, setEditCondition] = useState("");
  const [editAction, setEditAction] = useState("");

  async function refresh() {
    setLoading(true);
    try {
      const [r, d] = await Promise.all([
        agentContentApi.listDecisionRules(clinic.id),
        platformApi.listClinicDoctors(clinic.id),
      ]);
      setRules(r);
      setDoctors(d);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load decision rules");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [clinic.id]);

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault();
    if (!condition.trim() || !action.trim()) return;
    setSaving(true);
    setError(null);
    try {
      await agentContentApi.createDecisionRule(clinic.id, {
        condition: condition.trim(),
        action: action.trim(),
        priority,
        provider_id: providerId || undefined,
      });
      setCondition("");
      setAction("");
      setPriority(0);
      setProviderId("");
      await refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to add rule");
    } finally {
      setSaving(false);
    }
  }

  function startEdit(rule: AgentDecisionRule) {
    setEditingId(rule.id);
    setEditCondition(rule.condition);
    setEditAction(rule.action);
  }

  async function saveEdit(rule: AgentDecisionRule) {
    try {
      await agentContentApi.updateDecisionRule(clinic.id, rule.id, {
        condition: editCondition.trim(),
        action: editAction.trim(),
      });
      setEditingId(null);
      await refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to save rule");
    }
  }

  async function toggleActive(rule: AgentDecisionRule) {
    try {
      await agentContentApi.updateDecisionRule(clinic.id, rule.id, { is_active: !rule.is_active });
      await refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to update rule");
    }
  }

  async function handleDelete(rule: AgentDecisionRule) {
    try {
      await agentContentApi.deleteDecisionRule(clinic.id, rule.id);
      await refresh();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to delete rule");
    }
  }

  function doctorName(id: string | null) {
    if (!id) return "Every call (clinic-wide)";
    return doctors.find((d) => d.id === id)?.full_name ?? "Unknown doctor";
  }

  if (loading) return <div className="card">Loading…</div>;

  return (
    <div className="stack">
      <form className="card stack" onSubmit={handleAdd}>
        <strong>Add a rule</strong>
        <label className="stack" style={{ gap: 4 }}>
          <span style={{ fontSize: 13, color: "var(--color-text-muted)" }}>
            If the caller… (condition)
          </span>
          <input
            className="input"
            placeholder="e.g. describes chest pain or difficulty breathing"
            value={condition}
            onChange={(e) => setCondition(e.target.value)}
          />
        </label>
        <label className="stack" style={{ gap: 4 }}>
          <span style={{ fontSize: 13, color: "var(--color-text-muted)" }}>…then the agent should (action)</span>
          <textarea
            className="input"
            rows={2}
            placeholder="e.g. stop scheduling, tell them to hang up and call emergency services"
            value={action}
            onChange={(e) => setAction(e.target.value)}
          />
        </label>
        <div className="row" style={{ flexWrap: "wrap" }}>
          <label className="stack" style={{ gap: 4 }}>
            <span style={{ fontSize: 13, color: "var(--color-text-muted)" }}>Applies to</span>
            <select className="input" value={providerId} onChange={(e) => setProviderId(e.target.value)} style={{ width: 220 }}>
              <option value="">Every call (clinic-wide)</option>
              {doctors.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.full_name} only
                </option>
              ))}
            </select>
          </label>
          <label className="stack" style={{ gap: 4 }}>
            <span style={{ fontSize: 13, color: "var(--color-text-muted)" }}>Priority (lower checked first)</span>
            <input className="input" type="number" value={priority} onChange={(e) => setPriority(Number(e.target.value))} style={{ width: 120 }} />
          </label>
          <button className="btn btn-primary" type="submit" disabled={saving} style={{ alignSelf: "flex-end" }}>
            {saving ? "Adding…" : "+ Add rule"}
          </button>
        </div>
      </form>

      {error && <div className="error-text">{error}</div>}

      <div className="card">
        <table>
          <thead>
            <tr>
              <th>#</th>
              <th>If…</th>
              <th>Then…</th>
              <th>Applies to</th>
              <th>Active</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {rules.map((r) => (
              <tr key={r.id}>
                <td>{r.priority}</td>
                {editingId === r.id ? (
                  <>
                    <td>
                      <input className="input" value={editCondition} onChange={(e) => setEditCondition(e.target.value)} />
                    </td>
                    <td>
                      <textarea className="input" rows={2} value={editAction} onChange={(e) => setEditAction(e.target.value)} />
                    </td>
                    <td>{doctorName(r.provider_id)}</td>
                    <td>{r.is_active ? "Yes" : "No"}</td>
                    <td>
                      <div className="row">
                        <button className="btn btn-primary" onClick={() => saveEdit(r)}>
                          Save
                        </button>
                        <button className="btn" onClick={() => setEditingId(null)}>
                          Cancel
                        </button>
                      </div>
                    </td>
                  </>
                ) : (
                  <>
                    <td style={{ maxWidth: 260 }}>{r.condition}</td>
                    <td style={{ maxWidth: 320, color: "var(--color-text-muted)" }}>{r.action}</td>
                    <td>{doctorName(r.provider_id)}</td>
                    <td>
                      <label className="row" style={{ gap: 4 }}>
                        <input type="checkbox" checked={r.is_active} onChange={() => toggleActive(r)} />
                      </label>
                    </td>
                    <td>
                      <div className="row">
                        <button className="btn" onClick={() => startEdit(r)}>
                          Edit
                        </button>
                        <button className="btn" onClick={() => handleDelete(r)}>
                          Delete
                        </button>
                      </div>
                    </td>
                  </>
                )}
              </tr>
            ))}
            {rules.length === 0 && (
              <tr>
                <td colSpan={6} style={{ color: "var(--color-text-muted)" }}>
                  No decision rules yet for {clinic.name}.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
