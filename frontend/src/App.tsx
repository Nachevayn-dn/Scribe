import { Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider, useAuth } from "./auth/AuthContext";
import { RequireAuth, RequireRole } from "./auth/RequireRole";
import { NavBar } from "./components/layout/NavBar";
import { LoginPage } from "./pages/LoginPage";
import { SignupClinicPage } from "./pages/SignupClinicPage";
import { PatientListPage } from "./pages/PatientListPage";
import { DashboardPage } from "./pages/DashboardPage";
import { EncounterRecordingPage } from "./pages/EncounterRecordingPage";
import { ClinicAdminDashboard } from "./pages/ClinicAdminDashboard";
import { PreferencesSettingsPage } from "./pages/PreferencesSettingsPage";

function AppRoutes() {
  const { user } = useAuth();
  return (
    <>
      <NavBar />
      <Routes>
        <Route path="/login" element={user ? <Navigate to="/" replace /> : <LoginPage />} />
        <Route path="/signup" element={user ? <Navigate to="/" replace /> : <SignupClinicPage />} />
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
          path="/admin"
          element={
            <RequireRole roles={["SUPER_ADMIN"]}>
              <ClinicAdminDashboard />
            </RequireRole>
          }
        />
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
