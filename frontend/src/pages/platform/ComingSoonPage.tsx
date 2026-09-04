interface Props {
  title: string;
  description: string;
}

/** A truthful placeholder — Inbound/Outbound agents aren't built yet (see
 * the project plan: Scribe ships first). Better than a fake or hidden nav
 * item. */
export function ComingSoonPage({ title, description }: Props) {
  return (
    <div className="stack">
      <h1 style={{ fontSize: 22 }}>{title}</h1>
      <div className="card">
        <p style={{ margin: 0, color: "var(--color-text-muted)" }}>{description}</p>
        <p style={{ margin: "8px 0 0", fontSize: 13, color: "var(--color-text-muted)" }}>
          Not built yet — MedicDesk.ai ships the Scribe agent first.
        </p>
      </div>
    </div>
  );
}
