import { apiFetch } from "./client";
import type { ConventionTemplate } from "../types/models";

export async function listConventions(): Promise<ConventionTemplate[]> {
  return apiFetch<ConventionTemplate[]>("/api/conventions");
}

export async function getConvention(templateId: string): Promise<ConventionTemplate> {
  return apiFetch<ConventionTemplate>(`/api/conventions/${templateId}`);
}

export async function createConvention(data: {
  name: string;
  deck_recipe: string;
  seat_count: number;
  suggested_phases?: string[];
  suggested_settings?: Record<string, unknown>;
  notes?: Record<string, string>;
}): Promise<ConventionTemplate> {
  return apiFetch<ConventionTemplate>("/api/conventions", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function updateConvention(
  templateId: string,
  data: Partial<{
    name: string;
    deck_recipe: string;
    seat_count: number;
    suggested_phases: string[];
    suggested_settings: Record<string, unknown>;
    notes: Record<string, string>;
  }>,
): Promise<ConventionTemplate> {
  return apiFetch<ConventionTemplate>(`/api/conventions/${templateId}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export async function deleteConvention(templateId: string): Promise<void> {
  return apiFetch(`/api/conventions/${templateId}`, { method: "DELETE" });
}
