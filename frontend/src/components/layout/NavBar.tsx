import { Link, useLocation } from "react-router-dom";
import { useAuth } from "../../auth/AuthContext";
import { MedicDeskLogo } from "./MedicDeskLogo";
import { UserMenu } from "./UserMenu";

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

/** A nav link, styled small and un-underlined via .nav-link, with the
 * current section highlighted (prefix match, so /encounters/:id still
 * lights up "Sessions"). */
function NavItem({ to, label, pathname }: { to: string; label: string; pathname: string }) {
  const isActive = to === "/" ? pathname === "/" : pathname.startsWith(to);
  return (
    <Link to={to} className={isActive ? "nav-link active" : "nav-link"}>
      {label}
    </Link>
  );
}

export function NavBar() {
  const { user } = useAuth();
  const location = useLocation();
  const sectionLabel = sectionLabelFor(location.pathname);
  const pathname = location.pathname;

  if (!user) return null;

  return (
    <header
      style={{
        background: "var(--color-surface)",
      }}
    >
      <div
        className="page"
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "12px 20px",
          gap: 16,
          maxWidth: "100%",
          overflowX: "auto",
        }}
      >
        <div className="row" style={{ gap: 20, flexWrap: "nowrap" }}>
          <Link
            to="/"
            style={{ textDecoration: "none", display: "flex", alignItems: "center", gap: 8, flexShrink: 0 }}
          >
            {user.clinic_logo_url ? (
              <img
                src={user.clinic_logo_url}
                alt={user.clinic_branding_name ?? "Clinic logo"}
                style={{ width: 30, height: 30, borderRadius: "50%", objectFit: "cover", flexShrink: 0 }}
              />
            ) : (
              <MedicDeskLogo size={30} />
            )}
            <span className="stack" style={{ gap: 0 }}>
              <span style={{ fontWeight: 700, color: "var(--color-text)", fontSize: 15, lineHeight: 1.2 }}>
                {user.clinic_branding_name || "MedicDesk.ai"}
              </span>
              {sectionLabel && (
                <span style={{ fontSize: 10, color: "var(--color-primary)", lineHeight: 1.2 }}>
                  {sectionLabel}
                </span>
              )}
            </span>
          </Link>
          <nav className="row" style={{ gap: 14, flexWrap: "nowrap" }}>
            <NavItem to="/patients" label="Patients" pathname={pathname} />
            <NavItem to="/sessions" label="Sessions" pathname={pathname} />
            <NavItem to="/appointments" label="Appointments" pathname={pathname} />
            {(user.role === "PROVIDER" || user.role === "SUPER_ADMIN") && (
              <>
                <NavItem to="/templates" label="Templates" pathname={pathname} />
                <NavItem to="/preferences" label="Preferences" pathname={pathname} />
              </>
            )}
            <NavItem to="/settings" label="Settings" pathname={pathname} />
            {user.role === "SUPER_ADMIN" && <NavItem to="/admin" label="Clinic Admin" pathname={pathname} />}
            {user.is_platform_admin && <NavItem to="/platform" label="Platform" pathname={pathname} />}
          </nav>
        </div>

        <UserMenu />
      </div>
    </header>
  );
}
