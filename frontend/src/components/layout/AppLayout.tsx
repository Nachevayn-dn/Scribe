import { Outlet } from "react-router-dom";
import { AnnouncementGate } from "../common/AnnouncementGate";
import { ClinicSidebar } from "./ClinicSidebar";

/** Wraps every regular (non-platform) authenticated route: the existing top
 * NavBar stays exactly as it was (rendered separately, above this), and
 * this just adds the new left sidebar alongside the routed page content —
 * it does not replace anything. AnnouncementGate also lives here so a
 * pending platform-wide announcement shows up regardless of which page a
 * doctor lands on first. */
export function AppLayout() {
  return (
    <div style={{ display: "flex" }}>
      <AnnouncementGate />
      <ClinicSidebar />
      <div style={{ flex: 1, minWidth: 0 }}>
        <Outlet />
      </div>
    </div>
  );
}
