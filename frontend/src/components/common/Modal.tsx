import type { ReactNode } from "react";

interface Props {
  title: string;
  onClose: () => void;
  children: ReactNode;
}

/** A simple centered popup with a dimmed backdrop. Clicking the backdrop or
 * the close button both cancel — callers own committing via their own
 * buttons inside `children`. */
export function Modal({ title, onClose, children }: Props) {
  return (
    <div
      onClick={onClose}
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(15, 18, 25, 0.45)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 1000,
        padding: 20,
      }}
    >
      <div
        className="card stack"
        onClick={(e) => e.stopPropagation()}
        style={{ width: "100%", maxWidth: 420, boxShadow: "0 12px 40px rgba(0,0,0,0.25)" }}
      >
        <div className="row" style={{ justifyContent: "space-between" }}>
          <strong>{title}</strong>
          <button className="btn" onClick={onClose} aria-label="Close">
            ✕
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}
