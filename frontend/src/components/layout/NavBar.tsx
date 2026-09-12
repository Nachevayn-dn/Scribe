import { Link, useLocation } from "react-router-dom";
import { useAuth } from "../../auth/AuthContext";
import { DoctorAvatar } from "./DoctorAvatar";
import { LogoutLink } from "./LogoutLink";
import { MedicDeskLogo } from "./MedicDeskLogo";
import { ThemeSwitcher } from "./ThemeSwitcher";

const ROLE_LABELS: Record<string, string> = {
  PROVIDER: "Doctor",
  SUPER_ADMIN: "Admin",
  ASSISTANT: "Assistant",
};

/** The small label under the MedicDesk.ai wordmark — names whichever
 * product area the page belongs to, rather than always reading "Ambient
 * Scribe" regardless of where you actually are. Blank on the dashboard
 * itself. Ordered longest-prefix-first isn't needed here since none of
 * these prefixes nest inside each other. */
const SECTION_LABEL_BY_PATH_PREFIX: [string, string][] = [
  ["/sessions", "Ambient Scribe"],
  ["/encounters", "Ambient Scribe"],
  ["/clinic/inbound", "Inbound & Outbound Agents"],
  ["/clinic/outbound", "Inbound & Outbound Agents"],
  ["/clinic/analytics", "Analytics"],
];

function sectionLabelFor(pathname: string): string | null {
  const match = SECTION_LABEL_BY_PATH_PREFIX.find(([prefix]) => pathname.startsWith(prefix));
  return match ? match[1] : null;
}

export function NavBar() {
  const { user } = useAuth();
  const location = useLocation();
  const sectionLabel = sectionLabelFor(location.pathname);

  if (!user) return null;

  return (
    <header
      style={{
        background: "var(--color-surface)",
      }}
    >
      <div
        className="page"
        style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "14px 20px", gap: 20 }}
      >
        <div className="row" style={{ gap: 24, flexWrap: "wrap" }}>
          <Link to="/" style={{ textDecoration: "none", display: "flex", alignItems: "center", gap: 10 }}>
            <MedicDeskLogo size={34} />
            <span className="stack" style={{ gap: 0 }}>
              <span style={{ fontWeight: 700, color: "var(--color-text)", fontSize: 16, lineHeight: 1.2 }}>
                MedicDesk.ai
              </span>
              {sectionLabel && (
                <span style={{ fontSize: 11, color: "var(--color-primary)", lineHeight: 1.2 }}>
                  {sectionLabel}
                </span>
              )}
            </span>
          </Link>
          <div className="row">
            <Link to="/patients">Patients</Link>
            <Link to="/sessions">Sessions</Link>
            <Link to="/appointments">Appointments</Link>
            {(user.role === "PROVIDER" || user.role === "SUPER_ADMIN") && (
              <>
                <Link to="/templates">Templates</Link>
                <Link to="/preferences">Preferences</Link>
              </>
            )}
            <Link to="/settings">Settings</Link>
            {user.role === "SUPER_ADMIN" && <Link to="/admin">Clinic Admin</Link>}
            {user.is_platform_admin && <Link to="/platform">Platform</Link>}
          </div>
        </div>

        <div className="row" style={{ gap: 12 }}>
          <ThemeSwitcher />
          <DoctorAvatar />
          <div className="stack" style={{ gap: 2, minWidth: 0 }}>
            <span style={{ fontSize: 14, fontWeight: 600, whiteSpace: "nowrap" }}>{user.full_name}</span>
            <span style={{ fontSize: 12, color: "var(--color-text-muted)", whiteSpace: "nowrap" }}>
              {user.clinic_name}
            </span>
            <span className="badge" style={{ whiteSpace: "nowrap", width: "fit-content" }}>
              {ROLE_LABELS[user.role] ?? user.role}
            </span>
          </div>
          <LogoutLink />
        </div>
      </div>
    </header>
  );
}
