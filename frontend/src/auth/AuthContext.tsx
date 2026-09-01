import { createContext, useCallback, useContext, useEffect, useState } from "react";
import type { ReactNode } from "react";
import * as authApi from "../api/auth";
import { getToken, setToken } from "../api/client";
import type { CurrentUser } from "../types";

interface AuthContextValue {
  user: CurrentUser | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  signupClinic: (payload: {
    clinic_name: string;
    admin_email: string;
    admin_password: string;
    admin_full_name: string;
  }) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [loading, setLoading] = useState(true);

  const refreshMe = useCallback(async () => {
    if (!getToken()) {
      setUser(null);
      setLoading(false);
      return;
    }
    try {
      const me = await authApi.me();
      setUser(me);
    } catch {
      setToken(null);
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refreshMe();
  }, [refreshMe]);

  const login = useCallback(async (email: string, password: string) => {
    const { access_token } = await authApi.login(email, password);
    setToken(access_token);
    await refreshMe();
  }, [refreshMe]);

  const signupClinic = useCallback(
    async (payload: {
      clinic_name: string;
      admin_email: string;
      admin_password: string;
      admin_full_name: string;
    }) => {
      const { access_token } = await authApi.signupClinic(payload);
      setToken(access_token);
      await refreshMe();
    },
    [refreshMe],
  );

  const logout = useCallback(() => {
    setToken(null);
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, login, signupClinic, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within an AuthProvider");
  return ctx;
}
