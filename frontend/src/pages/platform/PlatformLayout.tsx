import { Link, Outlet } from "react-router-dom";
import { useAuth } from "../../auth/AuthContext";
import { LogoutLink } from "../../components/layout/LogoutLink";
import { Sidebar } from "../../components/layout/Sidebar";

/** Wraps every /platform/* route with the console's sidebar. Kept entirely
 * separate from the doctor-facing app's top NavBar/layout. */
export function PlatformLayout() {
  const { user } = useAuth();

  return (
    <div style={{ display: "flex", minHeight: "100vh" }}>
      <Sidebar />
      <div style={{ flex: 1, minWidth: 0 }}>
        <header
          style={{
            display: "flex",
            justifyContent: "flex-end",
            alignItems: "center",
            gap: 16,
            padding: "14px 24px",
          }}
        >
          <Link to="/" style={{ fontSize: 13 }}>
            ← Exit to app
          </Link>
          <span style={{ fontSize: 13, color: "var(--color-text-muted)" }}>{user?.full_name}</span>
          <LogoutLink />
        </header>
        <div className="page" style={{ maxWidth: 1100 }}>
          <Outlet />
        </div>
      </div>
    </div>
  );
}
