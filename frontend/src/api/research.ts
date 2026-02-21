import { apiFetch } from "./client";
import type { ResearchSession, SessionSPQAN, ResearchEvent } from "../types/models";

export async function listResearchSessions(params?: {
  date_from?: string;
  date_to?: string;
  deck_recipe?: string;
  has_ai?: boolean;
}): Promise<ResearchSession[]> {
  const qs = new URLSearchParams();
  if (params?.date_from) qs.set("date_from", params.date_from);
  if (params?.date_to) qs.set("date_to", params.date_to);
  if (params?.deck_recipe) qs.set("deck_recipe", params.deck_recipe);
  if (params?.has_ai !== undefined) qs.set("has_ai", String(params.has_ai));
  const q = qs.toString();
  return apiFetch<ResearchSession[]>(`/api/research/sessions${q ? `?${q}` : ""}`);
}

export async function computeMetrics(
  tableIds: string[],
  families?: string[],
): Promise<SessionSPQAN[]> {
  return apiFetch<SessionSPQAN[]>("/api/research/metrics/compute", {
    method: "POST",
    body: JSON.stringify({ table_ids: tableIds, families: families ?? null }),
  });
}

export async function getResearchEvents(
  tableId: string,
  params?: { from_seq?: number; to_seq?: number; event_type?: string },
): Promise<ResearchEvent[]> {
  const qs = new URLSearchParams();
  if (params?.from_seq !== undefined) qs.set("from_seq", String(params.from_seq));
  if (params?.to_seq !== undefined) qs.set("to_seq", String(params.to_seq));
  if (params?.event_type) qs.set("event_type", params.event_type);
  const q = qs.toString();
  return apiFetch<ResearchEvent[]>(`/api/research/sessions/${tableId}/events${q ? `?${q}` : ""}`);
}

export function exportResearchEventsUrl(tableId: string): string {
  return `/api/research/sessions/${tableId}/events/export`;
}
