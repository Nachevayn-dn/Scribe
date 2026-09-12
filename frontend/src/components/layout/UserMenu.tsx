import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
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
 * link across the header bar itself.
 *
 * The dropdown itself renders via a portal into document.body, positioned
 * from the trigger's own screen coordinates (position: fixed), rather than
 * as a normal absolutely-positioned child of the trigger. The header row it
 * lives in scrolls horizontally on narrow screens (see NavBar's
 * overflowX: "auto"), and CSS clips an overflow-x: auto container's
 * vertical overflow too unless overflow-y is set separately — a portal
 * sidesteps that (and any future ancestor overflow/stacking issue) instead
 * of relying on getting every ancestor's overflow/z-index exactly right. */
export function UserMenu() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [coords, setCoords] = useState<{ top: number; right: number } | null>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);

  function openMenu() {
    const rect = triggerRef.current?.getBoundingClientRect();
    if (rect) setCoords({ top: rect.bottom + 8, right: window.innerWidth - rect.right });
    setOpen(true);
  }

  useEffect(() => {
    if (!open) return;
    function handleClick(e: MouseEvent) {
      const target = e.target as Node;
      if (triggerRef.current?.contains(target) || menuRef.current?.contains(target)) return;
      setOpen(false);
    }
    function handleKey(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    // Anchored via fixed screen coordinates computed once on open — rather
    // than tracking scroll/resize to keep it glued to the trigger, just
    // close it, same as clicking away.
    function handleViewportChange() {
      setOpen(false);
    }
    document.addEventListener("mousedown", handleClick);
    document.addEventListener("keydown", handleKey);
    window.addEventListener("scroll", handleViewportChange, true);
    window.addEventListener("resize", handleViewportChange);
    return () => {
      document.removeEventListener("mousedown", handleClick);
      document.removeEventListener("keydown", handleKey);
      window.removeEventListener("scroll", handleViewportChange, true);
      window.removeEventListener("resize", handleViewportChange);
    };
  }, [open]);

  if (!user) return null;

  function handleLogout() {
    logout();
    navigate("/login");
  }

  return (
    <>
      <button
        ref={triggerRef}
        onClick={() => (open ? setOpen(false) : openMenu())}
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
          flexShrink: 0,
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

      {open &&
        coords &&
        createPortal(
          <div
            ref={menuRef}
            className="card stack"
            style={{
              position: "fixed",
              top: coords.top,
              right: coords.right,
              width: 240,
              gap: 12,
              zIndex: 1000,
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
          </div>,
          document.body,
        )}
    </>
  );
}
