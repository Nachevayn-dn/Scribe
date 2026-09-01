import { api } from "./client";
import type { CurrentUser } from "../types";

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export function signupClinic(payload: {
  clinic_name: string;
  admin_email: string;
  admin_password: string;
  admin_full_name: string;
}) {
  return api.post<TokenResponse>("/auth/signup-clinic", payload);
}

export function login(email: string, password: string) {
  return api.post<TokenResponse>("/auth/login", { email, password });
}

export function me() {
  return api.get<CurrentUser>("/auth/me");
}
