interface Props {
  label: string;
  value: number | string;
  hint?: string;
}

/** A single number-and-label tile, used for the "sessions this week" and
 * "scheduled appointments" widgets. */
export function StatWidget({ label, value, hint }: Props) {
  return (
    <div className="card stack" style={{ gap: 4, flex: 1, minWidth: 180 }}>
      <span style={{ fontSize: 13, color: "var(--color-text-muted)" }}>{label}</span>
      <span style={{ fontSize: 32, fontWeight: 700, color: "var(--color-primary)" }}>{value}</span>
      {hint && <span style={{ fontSize: 12, color: "var(--color-text-muted)" }}>{hint}</span>}
    </div>
  );
}
