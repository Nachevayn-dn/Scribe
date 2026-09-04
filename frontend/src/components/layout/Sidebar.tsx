import { useState } from "react";
import { NavLink } from "react-router-dom";
import { HelpFeedbackModal } from "../../pages/platform/HelpFeedbackModal";

const linkStyle = ({ isActive }: { isActive: boolean }): React.CSSProperties => ({
  display: "block",
  padding: "10px 16px",
  borderRadius: "var(--radius)",
  textDecoration: "none",
  fontSize: 14,
  fontWeight: isActive ? 600 : 500,
  color: isActive ? "var(--color-primary)" : "var(--color-text)",
  background: isActive ? "var(--color-primary-soft)" : "transparent",
});

function Divider() {
  return (
    <hr style={{ border: "none", borderTop: "1px solid var(--color-border)", width: "100%", margin: "8px 0" }} />
  );
}

/** The platform admin console's left nav — vertical, fixed to the console
 * layout only (see pages/platform/PlatformLayout.tsx). Not shown on the
 * regular doctor-facing app, which keeps its own top NavBar. */
export function Sidebar() {
  const [feedbackOpen, setFeedbackOpen] = useState(false);

  return (
    <nav
      style={{
        width: 220,
        flexShrink: 0,
        borderRight: "1px solid var(--color-border)",
        background: "var(--color-surface)",
        padding: "20px 12px",
        display: "flex",
        flexDirection: "column",
        minHeight: "100vh",
      }}
    >
      <div style={{ padding: "0 8px 20px" }}>
        <span style={{ fontWeight: 700, fontSize: 15 }}>MedicDesk.ai</span>
        <div style={{ fontSize: 11, color: "var(--color-text-muted)" }}>Platform admin</div>
      </div>

      <div className="stack" style={{ gap: 2, flex: 1 }}>
        <NavLink to="/platform/patients" style={linkStyle}>
          Patients
        </NavLink>
        <NavLink to="/platform/scribe" style={linkStyle}>
          Scribe
        </NavLink>
        <NavLink to="/platform/inbound" style={linkStyle}>
          Inbound agent
        </NavLink>
        <NavLink to="/platform/outbound" style={linkStyle}>
          Outbound agent
        </NavLink>

        <Divider />

        <NavLink to="/platform/settings" style={linkStyle}>
          Settings
        </NavLink>
        <NavLink to="/platform/preferences" style={linkStyle}>
          Preferences
        </NavLink>

        <Divider />

        <NavLink to="/platform/analytics" style={linkStyle}>
          Analytics
        </NavLink>
      </div>

      <button className="btn" style={{ width: "100%", justifyContent: "center" }} onClick={() => setFeedbackOpen(true)}>
        Help / Feedback
      </button>

      {feedbackOpen && <HelpFeedbackModal onClose={() => setFeedbackOpen(false)} />}
    </nav>
  );
}
