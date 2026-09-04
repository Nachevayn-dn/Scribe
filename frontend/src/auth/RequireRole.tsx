import type { ReactNode } from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "./AuthContext";
import type { UserRole } from "../types";

export function RequireAuth({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth();
  if (loading) return <div className="page">Loading…</div>;
  if (!user) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

export function RequireRole({ roles, children }: { roles: UserRole[]; children: ReactNode }) {
  const { user, loading } = useAuth();
  if (loading) return <div className="page">Loading…</div>;
  if (!user) return <Navigate to="/login" replace />;
  if (!roles.includes(user.role)) {
    return (
      <div className="page">
        <div className="card error-text">
          You don't have permission to view this page.
        </div>
      </div>
    );
  }
  return <>{children}</>;
}

/** Gates the platform console (see pages/platform/) — a MedicDesk operator
 * account, not a clinic's own SUPER_ADMIN. There's no self-serve way to
 * become one; is_platform_admin is flagged directly in the database. */
export function RequirePlatformAdmin({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth();
  if (loading) return <div className="page">Loading…</div>;
  if (!user) return <Navigate to="/login" replace />;
  if (!user.is_platform_admin) {
    return (
      <div className="page">
        <div className="card error-text">
          You don't have permission to view this page.
        </div>
      </div>
    );
  }
  return <>{children}</>;
}
