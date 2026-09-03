import { Link } from "react-router-dom";

interface Props {
  label: string;
  value: number | string;
  hint?: string;
  to?: string;
}

/** A single number-and-label tile, used for the "sessions this week" and
 * "scheduled appointments" widgets. Pass `to` to make the whole tile a link
 * (e.g. into the sessions list, pre-filtered). */
export function StatWidget({ label, value, hint, to }: Props) {
  const content = (
    <>
      <span style={{ fontSize: 13, color: "var(--color-text-muted)" }}>{label}</span>
      <span style={{ fontSize: 32, fontWeight: 700, color: "var(--color-primary)" }}>{value}</span>
      {hint && <span style={{ fontSize: 12, color: "var(--color-text-muted)" }}>{hint}</span>}
    </>
  );

  if (to) {
    return (
      <Link
        to={to}
        className="card stack"
        style={{ gap: 4, flex: 1, minWidth: 180, textDecoration: "none", color: "inherit" }}
      >
        {content}
      </Link>
    );
  }

  return (
    <div className="card stack" style={{ gap: 4, flex: 1, minWidth: 180 }}>
      {content}
    </div>
  );
}
