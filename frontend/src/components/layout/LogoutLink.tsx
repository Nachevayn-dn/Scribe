import { useNavigate } from "react-router-dom";
import { useAuth } from "../../auth/AuthContext";

/** A plain text "Log out" — used in both the NavBar and the platform
 * console's header, kept as one component so the elegant/subtle styling
 * (no button chrome) stays in sync. */
export function LogoutLink() {
  const { logout } = useAuth();
  const navigate = useNavigate();

  function handleLogout() {
    logout();
    navigate("/login");
  }

  return (
    <button
      onClick={handleLogout}
      style={{
        background: "none",
        border: "none",
        padding: 0,
        font: "inherit",
        fontSize: 13,
        color: "var(--color-primary)",
        cursor: "pointer",
      }}
    >
      Log out
    </button>
  );
}
