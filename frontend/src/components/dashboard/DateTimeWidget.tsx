import { useEffect, useState } from "react";
import { TIMEZONES } from "../../data/timezones";

const STORAGE_KEY = "scribe_dashboard_timezone";

function loadSavedTimezone(): string {
  try {
    return localStorage.getItem(STORAGE_KEY) || TIMEZONES[0].value;
  } catch {
    return TIMEZONES[0].value;
  }
}

/** Live clock with a timezone picker. The picker is a per-viewer UI
 * preference (not shared clinic data), so it's saved to localStorage rather
 * than the backend. */
export function DateTimeWidget() {
  const [timezone, setTimezone] = useState(loadSavedTimezone);
  const [now, setNow] = useState(() => new Date());

  useEffect(() => {
    const id = window.setInterval(() => setNow(new Date()), 1000);
    return () => window.clearInterval(id);
  }, []);

  function handleTimezoneChange(value: string) {
    setTimezone(value);
    try {
      localStorage.setItem(STORAGE_KEY, value);
    } catch {
      // localStorage unavailable (private mode, etc.) — selection just
      // won't persist across reloads, which is fine.
    }
  }

  const dateLabel = new Intl.DateTimeFormat(undefined, {
    timeZone: timezone,
    weekday: "short",
    year: "numeric",
    month: "short",
    day: "numeric",
  }).format(now);
  const timeLabel = new Intl.DateTimeFormat(undefined, {
    timeZone: timezone,
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  }).format(now);

  return (
    <div className="card stack" style={{ gap: 4, flex: 1, minWidth: 220 }}>
      <span style={{ fontSize: 13, color: "var(--color-text-muted)" }}>{dateLabel}</span>
      <span
        style={{
          fontSize: 32,
          fontWeight: 700,
          color: "var(--color-primary)",
          fontVariantNumeric: "tabular-nums",
        }}
      >
        {timeLabel}
      </span>
      <select
        className="input"
        value={timezone}
        onChange={(e) => handleTimezoneChange(e.target.value)}
        style={{ fontSize: 12, padding: "4px 6px" }}
      >
        {TIMEZONES.map((tz) => (
          <option key={tz.value} value={tz.value}>
            {tz.label}
          </option>
        ))}
      </select>
    </div>
  );
}
