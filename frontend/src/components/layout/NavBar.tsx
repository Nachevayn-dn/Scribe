import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../../auth/AuthContext";

export function NavBar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  if (!user) return null;

  function handleLogout() {
    logout();
    navigate("/login");
  }

  return (
    <header
      style={{
        borderBottom: "1px solid var(--color-border)",
        background: "var(--color-surface)",
      }}
    >
      <div
        className="page"
        style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "14px 20px" }}
      >
        <div className="row">
          <Link to="/" style={{ fontWeight: 700, textDecoration: "none", color: "var(--color-text)" }}>
            🩺 Scribe
          </Link>
          <Link to="/patients">Patients</Link>
          {(user.role === "PROVIDER" || user.role === "SUPER_ADMIN") && (
            <Link to="/preferences">Preferences</Link>
          )}
          {user.role === "SUPER_ADMIN" && <Link to="/admin">Clinic Admin</Link>}
        </div>
        <div className="row">
          <span className="badge">{user.role}</span>
          <span style={{ fontSize: 14 }}>{user.full_name}</span>
          <button className="btn" onClick={handleLogout}>
            Log out
          </button>
        </div>
      </div>
    </header>
  );
}
