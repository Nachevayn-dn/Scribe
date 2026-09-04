import { useState } from "react";
import { NavLink } from "react-router-dom";
import { HelpFeedbackModal } from "../common/HelpFeedbackModal";

interface NavItem {
  label: string;
  to: string;
}

interface Props {
  subtitle: string;
  /** Groups of links, rendered with a divider between groups (not before
   * the first). Mirrors how both the platform console and the clinic
   * sidebar are specified: a few items, a line, a few more. */
  sections: NavItem[][];
  /** Appended as the very last item, after one more divider — opens the
   * shared Help/Feedback modal. Styled identically to a nav link, not as
   * a separate button, so the menu just quietly ends with it. */
  showFeedback?: boolean;
}

const itemStyle: React.CSSProperties = {
  display: "block",
  width: "100%",
  textAlign: "left",
  padding: "10px 16px",
  borderRadius: "var(--radius)",
  border: "none",
  background: "transparent",
  textDecoration: "none",
  fontSize: 14,
  fontWeight: 500,
  color: "var(--color-text)",
  cursor: "pointer",
  font: "inherit",
};

const linkStyle = ({ isActive }: { isActive: boolean }): React.CSSProperties => ({
  ...itemStyle,
  fontWeight: isActive ? 600 : 500,
  color: isActive ? "var(--color-primary)" : "var(--color-text)",
  background: isActive ? "var(--color-primary-soft)" : "transparent",
});

function Divider() {
  return (
    <hr style={{ border: "none", borderTop: "1px solid var(--color-border)", width: "100%", margin: "8px 0" }} />
  );
}

/** The shared visual shape behind both left-hand menus in the app — the
 * platform admin console's sidebar and the doctor-facing clinic sidebar.
 * Each caller supplies its own title/sections; this owns only the layout,
 * active-link styling, and the trailing Help/Feedback item. */
export function VerticalNav({ subtitle, sections, showFeedback }: Props) {
  const [feedbackOpen, setFeedbackOpen] = useState(false);

  return (
    <nav
      style={{
        width: 220,
        flexShrink: 0,
        background: "var(--color-surface)",
        padding: "20px 12px",
        minHeight: "100vh",
      }}
    >
      <div style={{ padding: "0 8px 20px" }}>
        <span style={{ fontWeight: 700, fontSize: 15 }}>MedicDesk.ai</span>
        <div style={{ fontSize: 11, color: "var(--color-text-muted)" }}>{subtitle}</div>
      </div>

      <div className="stack" style={{ gap: 2 }}>
        {sections.map((section, i) => (
          <div key={i} className="stack" style={{ gap: 2 }}>
            {i > 0 && <Divider />}
            {section.map((item) => (
              <NavLink key={item.to} to={item.to} style={linkStyle}>
                {item.label}
              </NavLink>
            ))}
          </div>
        ))}

        {showFeedback && (
          <>
            <Divider />
            <button style={itemStyle} onClick={() => setFeedbackOpen(true)}>
              Help / Feedback
            </button>
          </>
        )}
      </div>

      {feedbackOpen && <HelpFeedbackModal onClose={() => setFeedbackOpen(false)} />}
    </nav>
  );
}
