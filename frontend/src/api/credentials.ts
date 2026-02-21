import { apiFetch } from "./client";
import type { CredentialPublic, CredentialWithSecret } from "../types/models";

export async function listCredentials(): Promise<CredentialPublic[]> {
  return apiFetch<CredentialPublic[]>("/api/credentials");
}

export async function createCredential(displayName: string): Promise<CredentialWithSecret> {
  return apiFetch<CredentialWithSecret>("/api/credentials", {
    method: "POST",
    body: JSON.stringify({ display_name: displayName }),
  });
}

export async function revokeCredential(credentialId: string): Promise<void> {
  return apiFetch(`/api/credentials/${credentialId}`, { method: "DELETE" });
}
