import { apiFetch } from "./client";
import type { Event, GameSummary, TableMeta } from "../types/models";

export async function listGames(): Promise<TableMeta[]> {
  return apiFetch<TableMeta[]>("/api/games");
}

export async function getEvents(
  tableId: string,
  fromSeq?: number,
  toSeq?: number,
): Promise<Event[]> {
  const params = new URLSearchParams();
  if (fromSeq !== undefined) params.set("from_seq", String(fromSeq));
  if (toSeq !== undefined) params.set("to_seq", String(toSeq));
  const qs = params.toString();
  return apiFetch<Event[]>(`/api/tables/${tableId}/events${qs ? `?${qs}` : ""}`);
}

export async function getSummary(tableId: string): Promise<GameSummary> {
  return apiFetch<GameSummary>(`/api/tables/${tableId}/summary`);
}
