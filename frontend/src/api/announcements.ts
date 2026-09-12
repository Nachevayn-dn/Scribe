import { ApiError, api, getToken } from "./client";
import type { Announcement } from "../types";

/** Active announcements this user hasn't acknowledged yet, oldest first —
 * the must-acknowledge popup (see components/common/AnnouncementGate.tsx)
 * shows them one at a time. */
export function listPendingAnnouncements() {
  return api.get<Announcement[]>("/announcements/pending");
}

export function acknowledgeAnnouncement(announcementId: string) {
  return api.post<void>(`/announcements/${announcementId}/acknowledge`);
}

/** Videos are served through an authenticated endpoint, so a plain <video
 * src> won't work — fetch it as a blob and hand the element an object URL,
 * same approach as platform.ts's downloadClinicDocument. */
export async function fetchAnnouncementVideoUrl(announcementId: string): Promise<string> {
  const token = getToken();
  const res = await fetch(`/api/v1/announcements/${announcementId}/video`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!res.ok) throw new ApiError(res.status, "Failed to load video");
  const blob = await res.blob();
  return URL.createObjectURL(blob);
}
