import { apiFetch } from "./client";
import type { ConsentRecord } from "../types/models";
import type { ConsentTier } from "../types/enums";

export interface ConsentRequirements {
  required: ConsentTier[];
  optional: ConsentTier[];
}

export async function getConsentRequirements(
  tableId: string,
): Promise<ConsentRequirements> {
  return apiFetch<ConsentRequirements>(
    `/api/tables/${tableId}/consent/requirements`,
  );
}

export async function submitConsent(
  tableId: string,
  tiers: Record<string, boolean>,
): Promise<ConsentRecord> {
  return apiFetch<ConsentRecord>(`/api/tables/${tableId}/consent`, {
    method: "POST",
    body: JSON.stringify({ tiers }),
  });
}

export async function getConsent(
  tableId: string,
): Promise<ConsentRecord | null> {
  try {
    return await apiFetch<ConsentRecord>(`/api/tables/${tableId}/consent`);
  } catch {
    return null;
  }
}

export async function revokeConsent(tableId: string): Promise<void> {
  return apiFetch<void>(`/api/tables/${tableId}/consent`, {
    method: "DELETE",
  });
}
