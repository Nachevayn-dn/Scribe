import { ENTITY_COLORS } from "../../styles/entityColors";
import type { EntityType } from "../../types";

export function EntityLegend() {
  const types = Object.keys(ENTITY_COLORS) as EntityType[];
  return (
    <div className="row" style={{ flexWrap: "wrap", gap: 10 }}>
      {types.map((type) => {
        const color = ENTITY_COLORS[type];
        return (
          <span
            key={type}
            className="row"
            style={{ gap: 6, fontSize: 12, color: "var(--color-text-muted)" }}
          >
            <span
              style={{
                width: 10,
                height: 10,
                borderRadius: 3,
                background: color.bg,
                border: `1px solid ${color.border}`,
                display: "inline-block",
              }}
            />
            {color.label}
          </span>
        );
      })}
    </div>
  );
}
