/** A "quick-add" Google Calendar link — no OAuth, no API key. It opens
 * Google Calendar pre-filled; the person still clicks Save there. Real
 * automatic sync would need a Google Cloud OAuth app, which hasn't been set
 * up — this is the no-setup middle ground, shared by every place in the app
 * that offers to add something to Google Calendar. */
const DEFAULT_EVENT_MINUTES = 30;

export function googleCalendarQuickAddUrl(opts: {
  title: string;
  start: Date;
  details?: string;
  minutes?: number;
}): string {
  const { title, start, details, minutes = DEFAULT_EVENT_MINUTES } = opts;
  const end = new Date(start.getTime() + minutes * 60 * 1000);
  const fmt = (d: Date) => d.toISOString().replace(/[-:]|\.\d{3}/g, "");
  const params = new URLSearchParams({
    action: "TEMPLATE",
    text: title,
    dates: `${fmt(start)}/${fmt(end)}`,
  });
  if (details) params.set("details", details);
  return `https://calendar.google.com/calendar/render?${params.toString()}`;
}
