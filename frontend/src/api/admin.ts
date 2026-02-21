import { apiFetch } from "./client";
import type { CredentialPublic, PrincipalInfo, ResearchHealth } from "../types/models";

export async function listPrincipals(): Promise<PrincipalInfo[]> {
  return apiFetch<PrincipalInfo[]>("/api/admin/principals");
}

export async function deletePrincipal(identityId: string): Promise<void> {
  return apiFetch(`/api/admin/principals/${identityId}`, { method: "DELETE" });
}

export async function listAllCredentials(): Promise<CredentialPublic[]> {
  return apiFetch<CredentialPublic[]>("/api/admin/credentials");
}

export async function adminRevokeCredential(credentialId: string): Promise<void> {
  return apiFetch(`/api/admin/credentials/${credentialId}`, { method: "DELETE" });
}

export async function getResearchHealth(): Promise<ResearchHealth> {
  return apiFetch<ResearchHealth>("/api/admin/research/health");
}
