import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../../auth/AuthContext";
import { DoctorAvatar } from "./DoctorAvatar";
import { ThemeSwitcher } from "./ThemeSwitcher";

const ROLE_LABELS: Record<string, string> = {
  PROVIDER: "Doctor",
  SUPER_ADMIN: "Admin",
  ASSISTANT: "Assistant",
};

/** The doctor-corner control in the top-right of the NavBar. Collapses the
 * avatar + name into a single trigger that opens a small dropdown with
 * account info, a prominent "Log out" right up top, and the color-scheme
 * picker under its own "Customize your platform" label below — instead of
 * spreading the theme swatches, name/clinic/badge stack, and a bare log-out
 * link across the header bar itself. */
export function UserMenu() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    function handleClick(e: MouseEvent) {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) setOpen(false);
    }
    function handleKey(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", handleClick);
    document.addEventListener("keydown", handleKey);
    return () => {
      document.removeEventListener("mousedown", handleClick);
      document.removeEventListener("keydown", handleKey);
    };
  }, [open]);

  if (!user) return null;

  function handleLogout() {
    logout();
    navigate("/login");
  }

  return (
    <div ref={rootRef} style={{ position: "relative", flexShrink: 0 }}>
      <button
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        aria-haspopup="true"
        style={{
          display: "flex",
          alignItems: "center",
          gap: 9,
          background: "none",
          border: "none",
          padding: "4px 6px",
          borderRadius: "var(--radius)",
          cursor: "pointer",
        }}
        onMouseDown={(e) => e.preventDefault()}
      >
        <DoctorAvatar size={34} />
        <span className="stack" style={{ gap: 0, alignItems: "flex-start" }}>
          <span
            style={{
              fontSize: 14,
              fontWeight: 600,
              letterSpacing: "0.01em",
              color: "var(--color-text)",
              whiteSpace: "nowrap",
            }}
          >
            {user.full_name}
          </span>
          <span style={{ fontSize: 11, color: "var(--color-text-muted)", whiteSpace: "nowrap" }}>
            {user.clinic_name}
          </span>
        </span>
      </button>

      {open && (
        <div
          className="card stack"
          style={{
            position: "absolute",
            top: "calc(100% + 8px)",
            right: 0,
            width: 240,
            gap: 12,
            zIndex: 50,
            boxShadow: "0 10px 28px rgba(0, 0, 0, 0.35)",
          }}
        >
          <div className="stack" style={{ gap: 2 }}>
            <span style={{ fontSize: 15, fontWeight: 600, letterSpacing: "0.01em" }}>{user.full_name}</span>
            <span style={{ fontSize: 12, color: "var(--color-text-muted)" }}>{user.clinic_name}</span>
            <span className="badge" style={{ width: "fit-content", marginTop: 4 }}>
              {ROLE_LABELS[user.role] ?? user.role}
            </span>
          </div>

          <button className="btn" onClick={handleLogout} style={{ justifyContent: "center" }}>
            Log out
          </button>

          <div style={{ height: 1, background: "var(--color-border)" }} />

          <div className="stack" style={{ gap: 6 }}>
            <span
              style={{
                fontSize: 11,
                color: "var(--color-text-muted)",
                textTransform: "uppercase",
                letterSpacing: "0.06em",
              }}
            >
              Customize your platform
            </span>
            <ThemeSwitcher />
          </div>
        </div>
      )}
    </div>
  );
}
