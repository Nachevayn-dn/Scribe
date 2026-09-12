import { api } from "./client";
import type { DailyRecap, DashboardSummary } from "../types";

export function getDashboardSummary() {
  return api.get<DashboardSummary>("/dashboard/summary");
}

/** Generated once per calendar day and cached server-side — safe to call
 * on every dashboard load. */
export function getDailyRecap() {
  return api.get<DailyRecap>("/dashboard/recap");
}
