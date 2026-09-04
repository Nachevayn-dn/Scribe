import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import { AuthProvider, useAuth } from "./auth/AuthContext";
import { RequireAuth, RequirePlatformAdmin, RequireRole } from "./auth/RequireRole";
import { AppLayout } from "./components/layout/AppLayout";
import { NavBar } from "./components/layout/NavBar";
import { ComingSoonPage } from "./components/common/ComingSoonPage";
import { LoginPage } from "./pages/LoginPage";
import { SignupClinicPage } from "./pages/SignupClinicPage";
import { PatientListPage } from "./pages/PatientListPage";
import { DashboardPage } from "./pages/DashboardPage";
import { EncounterRecordingPage } from "./pages/EncounterRecordingPage";
import { SessionsListPage } from "./pages/SessionsListPage";
import { AppointmentsPage } from "./pages/AppointmentsPage";
import { ClinicAdminDashboard } from "./pages/ClinicAdminDashboard";
import { ClinicAnalyticsPage } from "./pages/ClinicAnalyticsPage";
import { PreferencesSettingsPage } from "./pages/PreferencesSettingsPage";
import { IntegrationsPage } from "./pages/IntegrationsPage";
import { PlatformLayout } from "./pages/platform/PlatformLayout";
import { PlatformPatientsPage } from "./pages/platform/PlatformPatientsPage";
import { PlatformScribePage } from "./pages/platform/PlatformScribePage";
import { PlatformSettingsPage } from "./pages/platform/PlatformSettingsPage";
import { PlatformPreferencesPage } from "./pages/platform/PlatformPreferencesPage";
import { PlatformAnalyticsPage } from "./pages/platform/PlatformAnalyticsPage";

function AppRoutes() {
  const { user } = useAuth();
  const location = useLocation();
  const inPlatformConsole = location.pathname.startsWith("/platform");
  return (
    <>
      {!inPlatformConsole && <NavBar />}
      <Routes>
        <Route path="/login" element={user ? <Navigate to="/" replace /> : <LoginPage />} />
        <Route path="/signup" element={user ? <Navigate to="/" replace /> : <SignupClinicPage />} />

        {/* Regular authenticated app — top NavBar (above) plus this new
            left sidebar (AppLayout), side by side. Nothing here replaces
            the NavBar's own links. */}
        <Route element={<AppLayout />}>
          <Route
            path="/"
            element={
              <RequireAuth>
                <DashboardPage />
              </RequireAuth>
            }
          />
          <Route
            path="/patients"
            element={
              <RequireAuth>
                <PatientListPage />
              </RequireAuth>
            }
          />
          <Route
            path="/sessions"
            element={
              <RequireAuth>
                <SessionsListPage />
              </RequireAuth>
            }
          />
          <Route
            path="/appointments"
            element={
              <RequireAuth>
                <AppointmentsPage />
              </RequireAuth>
            }
          />
          <Route
            path="/encounters/:encounterId"
            element={
              <RequireAuth>
                <EncounterRecordingPage />
              </RequireAuth>
            }
          />
          <Route
            path="/preferences"
            element={
              <RequireRole roles={["PROVIDER", "SUPER_ADMIN"]}>
                <PreferencesSettingsPage />
              </RequireRole>
            }
          />
          <Route
            path="/integrations"
            element={
              <RequireAuth>
                <IntegrationsPage />
              </RequireAuth>
            }
          />
          <Route
            path="/admin"
            element={
              <RequireRole roles={["SUPER_ADMIN"]}>
                <ClinicAdminDashboard />
              </RequireRole>
            }
          />
          <Route
            path="/clinic/analytics"
            element={
              <RequireAuth>
                <ClinicAnalyticsPage />
              </RequireAuth>
            }
          />
          <Route
            path="/clinic/inbound"
            element={
              <RequireAuth>
                <ComingSoonPage title="Inbound agent" description="Handles incoming patient calls — scheduling, triage, and FAQs." />
              </RequireAuth>
            }
          />
          <Route
            path="/clinic/outbound"
            element={
              <RequireAuth>
                <ComingSoonPage title="Outbound agent" description="Places outbound calls — reminders, follow-ups, and check-ins." />
              </RequireAuth>
            }
          />
        </Route>

        <Route
          path="/platform"
          element={
            <RequirePlatformAdmin>
              <PlatformLayout />
            </RequirePlatformAdmin>
          }
        >
          <Route index element={<Navigate to="patients" replace />} />
          <Route path="patients" element={<PlatformPatientsPage />} />
          <Route path="scribe" element={<PlatformScribePage />} />
          <Route
            path="inbound"
            element={<ComingSoonPage title="Inbound agent" description="Handles incoming patient calls — scheduling, triage, and FAQs." />}
          />
          <Route
            path="outbound"
            element={<ComingSoonPage title="Outbound agent" description="Places outbound calls — reminders, follow-ups, and check-ins." />}
          />
          <Route path="settings" element={<PlatformSettingsPage />} />
          <Route path="preferences" element={<PlatformPreferencesPage />} />
          <Route path="analytics" element={<PlatformAnalyticsPage />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </>
  );
}

export function App() {
  return (
    <AuthProvider>
      <AppRoutes />
    </AuthProvider>
  );
}
