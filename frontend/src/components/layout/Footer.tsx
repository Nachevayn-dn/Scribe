/** A quiet footer, shown at the bottom of every page regardless of layout
 * (mounted once in App.tsx, outside NavBar/sidebar structures). */
export function Footer() {
  return (
    <footer style={{ padding: "24px 20px", textAlign: "center" }}>
      <span style={{ fontSize: 12, color: "var(--color-text-muted)" }}>
        MedicDesk.ai — All rights reserved {new Date().getFullYear()}
      </span>
    </footer>
  );
}
