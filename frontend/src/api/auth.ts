import { apiFetch } from "./client";
import type { BootstrapResponse, TokenResponse } from "../types/models";

export async function bootstrap(
  displayName: string,
): Promise<BootstrapResponse> {
  return apiFetch<BootstrapResponse>("/dev/bootstrap", {
    method: "POST",
    body: JSON.stringify({
      display_name: displayName,
      num_credentials: 1,
      credential_prefix: displayName.toLowerCase().replace(/\s+/g, "_"),
    }),
  });
}

export async function getToken(
  clientId: string,
  clientSecret: string,
): Promise<TokenResponse> {
  return apiFetch<TokenResponse>("/api/token", {
    method: "POST",
    body: JSON.stringify({
      client_id: clientId,
      client_secret: clientSecret,
    }),
  });
}
