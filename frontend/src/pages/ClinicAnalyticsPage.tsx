import { useEffect, useState } from "react";
import * as dashboardApi from "../api/dashboard";
import { StatWidget } from "../components/dashboard/StatWidget";
import { ApiError } from "../api/client";
import type { DashboardSummary } from "../types";

/** A doctor's own analytics — reuses the same role-scoped counts as the
 * dashboard widgets (own sessions if PROVIDER, assigned providers' if
 * ASSISTANT, clinic-wide if SUPER_ADMIN). Distinct from the platform
 * console's Analytics, which rolls up across every clinic. */
export function ClinicAnalyticsPage() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    dashboardApi
      .getDashboardSummary()
      .then(setSummary)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load analytics"))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="page">Loading…</div>;

  return (
    <div className="page stack">
      <h1 style={{ fontSize: 22 }}>Analytics</h1>
      {error && <div className="error-text">{error}</div>}
      <div className="row" style={{ flexWrap: "wrap" }}>
        <StatWidget label="Scribe sessions" value={summary?.sessions_this_week ?? 0} hint="Last 7 days" />
        <StatWidget
          label="Sessions marked scheduled"
          value={summary?.scheduled_appointment_sessions_this_week ?? 0}
          hint="Last 7 days"
        />
        <StatWidget label="Upcoming appointments" value={summary?.upcoming_appointments ?? 0} hint="Next 7 days" />
      </div>
    </div>
  );
}
