import { apiFetch } from "./client";
import type {
  TableState,
  TableSummary,
  Seat,
  TableSettings,
} from "../types/models";
import type { DeckRecipe } from "../types/enums";

export interface CreateTableRequest {
  display_name: string;
  deck_recipe: DeckRecipe;
  max_seats: number;
  research_mode?: boolean;
}

export async function listTables(): Promise<TableSummary[]> {
  return apiFetch<TableSummary[]>("/api/tables");
}

export async function getTable(tableId: string): Promise<TableState> {
  return apiFetch<TableState>(`/api/tables/${tableId}`);
}

export async function createTable(
  req: CreateTableRequest,
): Promise<TableState> {
  return apiFetch<TableState>("/api/tables", {
    method: "POST",
    body: JSON.stringify(req),
  });
}

export async function joinTable(
  tableId: string,
  displayName: string,
): Promise<Seat> {
  return apiFetch<Seat>(`/api/tables/${tableId}/join`, {
    method: "POST",
    body: JSON.stringify({ display_name: displayName }),
  });
}

export async function leaveTable(tableId: string): Promise<void> {
  return apiFetch<void>(`/api/tables/${tableId}/leave`, { method: "POST" });
}

export async function destroyTable(tableId: string): Promise<void> {
  return apiFetch<void>(`/api/tables/${tableId}`, { method: "DELETE" });
}

export async function updateSettings(
  tableId: string,
  settings: Partial<TableSettings>,
): Promise<TableSettings> {
  return apiFetch<TableSettings>(`/api/tables/${tableId}/settings`, {
    method: "PATCH",
    body: JSON.stringify(settings),
  });
}
