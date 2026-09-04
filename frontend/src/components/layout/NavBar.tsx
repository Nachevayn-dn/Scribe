import { Link } from "react-router-dom";
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

export function NavBar() {
  const { user } = useAuth();

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
              <span style={{ fontSize: 11, color: "var(--color-primary)", lineHeight: 1.2 }}>
                Ambient Scribe
              </span>
            </span>
          </Link>
          <div className="row">
            <Link to="/patients">Patients</Link>
            <Link to="/sessions">Sessions</Link>
            <Link to="/appointments">Appointments</Link>
            {(user.role === "PROVIDER" || user.role === "SUPER_ADMIN") && (
              <Link to="/preferences">Preferences</Link>
            )}
            <Link to="/integrations">Integrations</Link>
            {user.role === "SUPER_ADMIN" && <Link to="/admin">Clinic Admin</Link>}
            {user.is_platform_admin && <Link to="/platform">Platform</Link>}
          </div>
        </div>

        <div className="row" style={{ gap: 12 }}>
          <ThemeSwitcher />
          <DoctorAvatar />
          <div className="stack" style={{ gap: 2, minWidth: 0 }}>
            <span style={{ fontSize: 14, fontWeight: 600, whiteSpace: "nowrap" }}>{user.full_name}</span>
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
