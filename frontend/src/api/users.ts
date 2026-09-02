import { api } from "./client";
import type { User, UserRole } from "../types";

export function listUsers() {
  return api.get<User[]>("/users");
}

export function myAssignedProviders() {
  return api.get<User[]>("/users/me/assigned-providers");
}

export function createUser(payload: {
  email: string;
  password: string;
  full_name: string;
  role: UserRole;
  license_number?: string;
}) {
  return api.post<User>("/users", payload);
}

export function updateUser(id: string, payload: Partial<Pick<User, "full_name" | "role" | "is_active" | "license_number">>) {
  return api.patch<User>(`/users/${id}`, payload);
}

export function uploadMyPhoto(file: File) {
  const form = new FormData();
  form.append("file", file);
  return api.postForm<User>("/users/me/photo", form);
}

export function assignAssistant(providerId: string, assistantId: string) {
  return api.post<{ status: string }>(`/users/${providerId}/assistants/${assistantId}`);
}

export function unassignAssistant(providerId: string, assistantId: string) {
  return api.del<void>(`/users/${providerId}/assistants/${assistantId}`);
}
