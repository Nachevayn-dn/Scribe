import { Outlet } from "react-router-dom";
import { ClinicSidebar } from "./ClinicSidebar";

/** Wraps every regular (non-platform) authenticated route: the existing top
 * NavBar stays exactly as it was (rendered separately, above this), and
 * this just adds the new left sidebar alongside the routed page content —
 * it does not replace anything. */
export function AppLayout() {
  return (
    <div style={{ display: "flex" }}>
      <ClinicSidebar />
      <div style={{ flex: 1, minWidth: 0 }}>
        <Outlet />
      </div>
    </div>
  );
}
