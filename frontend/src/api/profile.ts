import { apiFetch } from "./client";
import type { ProfileInfo } from "../types/models";

export async function getProfile(): Promise<ProfileInfo> {
  return apiFetch<ProfileInfo>("/api/profile");
}

export async function updateProfile(displayName: string): Promise<ProfileInfo> {
  return apiFetch<ProfileInfo>("/api/profile", {
    method: "PATCH",
    body: JSON.stringify({ display_name: displayName }),
  });
}

export async function exportData(): Promise<{ tables: unknown[]; total_tables: number }> {
  return apiFetch("/api/profile/data-export");
}

export async function deleteAccount(): Promise<void> {
  return apiFetch("/api/profile", { method: "DELETE" });
}
