import { useEffect, useState } from "react";
import * as announcementsApi from "../../api/announcements";
import type { Announcement } from "../../types";

/** A platform-admin broadcast the doctor must acknowledge before it goes
 * away — no backdrop-click or ✕ dismissal, unlike the shared Modal
 * component, since "Got it" is meant to actually be clicked. Mounted once
 * in AppLayout so it shows up regardless of which page a doctor lands on
 * first. Works through a queue: acknowledging one immediately shows the
 * next pending one, if any — there's no history/bell, by design. */
export function AnnouncementGate() {
  const [queue, setQueue] = useState<Announcement[]>([]);
  const [videoUrl, setVideoUrl] = useState<string | null>(null);
  const [acking, setAcking] = useState(false);

  useEffect(() => {
    announcementsApi
      .listPendingAnnouncements()
      .then(setQueue)
      .catch(() => setQueue([]));
  }, []);

  const current = queue[0] ?? null;

  useEffect(() => {
    setVideoUrl(null);
    if (!current?.has_video) return;
    let cancelled = false;
    let objectUrl: string | null = null;
    announcementsApi.fetchAnnouncementVideoUrl(current.id).then((url) => {
      if (cancelled) {
        URL.revokeObjectURL(url);
        return;
      }
      objectUrl = url;
      setVideoUrl(url);
    });
    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [current?.id, current?.has_video]);

  if (!current) return null;

  async function handleAcknowledge() {
    setAcking(true);
    try {
      await announcementsApi.acknowledgeAnnouncement(current!.id);
      setQueue((prev) => prev.slice(1));
    } finally {
      setAcking(false);
    }
  }

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(15, 18, 25, 0.55)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 2000,
        padding: 20,
      }}
    >
      <div className="card stack" style={{ width: "100%", maxWidth: 480, boxShadow: "0 12px 40px rgba(0,0,0,0.3)" }}>
        <strong style={{ fontSize: 16 }}>{current.title || "An update from MedicDesk.ai"}</strong>
        <p style={{ margin: 0, whiteSpace: "pre-wrap" }}>{current.message}</p>
        {current.has_video && (
          videoUrl ? (
            <video controls src={videoUrl} style={{ width: "100%", borderRadius: 8 }} />
          ) : (
            <div style={{ fontSize: 13, color: "var(--color-text-muted)" }}>Loading video…</div>
          )
        )}
        <div className="row" style={{ justifyContent: "flex-end" }}>
          <button className="btn btn-primary" onClick={handleAcknowledge} disabled={acking}>
            {acking ? "…" : "Got it"}
          </button>
        </div>
      </div>
    </div>
  );
}
