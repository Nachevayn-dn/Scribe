import { VerticalNav } from "./VerticalNav";

/** The platform admin console's left nav — fixed to the console layout only
 * (see pages/platform/PlatformLayout.tsx). Not shown on the regular
 * doctor-facing app, which has its own ClinicSidebar alongside its NavBar. */
export function Sidebar() {
  return (
    <VerticalNav
      subtitle="Platform admin"
      sections={[
        [
          { label: "Patients", to: "/platform/patients" },
          { label: "Scribe", to: "/platform/scribe" },
          { label: "Inbound agent", to: "/platform/inbound" },
          { label: "Outbound agent", to: "/platform/outbound" },
        ],
        [
          { label: "Settings", to: "/platform/settings" },
          { label: "Preferences", to: "/platform/preferences" },
        ],
        [{ label: "Analytics", to: "/platform/analytics" }],
      ]}
      showFeedback
    />
  );
}
