import { useEffect, useState } from "react";
import * as platformApi from "../../api/platform";
import { StatWidget } from "../../components/dashboard/StatWidget";
import { ApiError } from "../../api/client";
import type { PlatformAnalytics } from "../../types";

export function PlatformAnalyticsPage() {
  const [analytics, setAnalytics] = useState<PlatformAnalytics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    platformApi
      .getAnalytics()
      .then(setAnalytics)
      .catch((err) => setError(err instanceof ApiError ? err.message : "Failed to load analytics"))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="page">Loading…</div>;

  return (
    <div className="stack">
      <h1 style={{ fontSize: 22 }}>Analytics</h1>
      {error && <div className="error-text">{error}</div>}
      <div className="row" style={{ flexWrap: "wrap" }}>
        <StatWidget label="Clinics" value={analytics?.clinics_count ?? 0} />
        <StatWidget label="Active doctors" value={analytics?.active_doctors_count ?? 0} />
        <StatWidget label="Scribe sessions" value={analytics?.sessions_this_week ?? 0} hint="Last 7 days, all clinics" />
        <StatWidget label="Notes signed" value={analytics?.notes_signed_this_week ?? 0} hint="Last 7 days, all clinics" />
      </div>
    </div>
  );
}
