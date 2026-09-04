import { useAuth } from "../../auth/AuthContext";
import { VerticalNav } from "./VerticalNav";

/** The doctor-facing left nav — sits alongside the existing top NavBar (not
 * a replacement for it) on every authenticated main-app page. Self-guards
 * on auth state the same way NavBar does, since AppLayout renders it
 * outside the per-route RequireAuth/RequireRole checks. */
export function ClinicSidebar() {
  const { user } = useAuth();
  if (!user) return null;

  return (
    <VerticalNav
      subtitle="Clinic"
      sections={[
        [
          { label: "Patients", to: "/patients" },
          { label: "Inbound agent", to: "/clinic/inbound" },
          { label: "Outbound agent", to: "/clinic/outbound" },
        ],
        [{ label: "Analytics", to: "/clinic/analytics" }],
      ]}
      showFeedback
    />
  );
}
