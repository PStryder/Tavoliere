import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import { Header } from "../components/layout/Header";
import { listCredentials, createCredential, revokeCredential } from "../api/credentials";
import type { CredentialPublic, CredentialWithSecret } from "../types/models";

export function ApiKeysPage() {
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();
  const [credentials, setCredentials] = useState<CredentialPublic[]>([]);
  const [loading, setLoading] = useState(true);
  const [newName, setNewName] = useState("");
  const [creating, setCreating] = useState(false);
  const [created, setCreated] = useState<CredentialWithSecret | null>(null);
  const [copied, setCopied] = useState<"id" | "secret" | null>(null);

  useEffect(() => {
    if (!isAuthenticated) {
      navigate("/");
      return;
    }
    loadCredentials();
  }, [isAuthenticated, navigate]);

  function loadCredentials() {
    listCredentials()
      .then(setCredentials)
      .catch(() => {})
      .finally(() => setLoading(false));
  }

  async function handleCreate() {
    if (!newName.trim()) return;
    setCreating(true);
    try {
      const cred = await createCredential(newName.trim());
      setCreated(cred);
      setNewName("");
      loadCredentials();
    } catch {
      /* empty */
    } finally {
      setCreating(false);
    }
  }

  async function handleRevoke(id: string) {
    if (!confirm("Revoke this credential? The AI agent using it will lose access.")) return;
    try {
      await revokeCredential(id);
      loadCredentials();
    } catch {
      /* empty */
    }
  }

  function copyToClipboard(text: string, which: "id" | "secret") {
    navigator.clipboard.writeText(text);
    setCopied(which);
    setTimeout(() => setCopied(null), 2000);
  }

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      <Header />
      <div className="max-w-3xl mx-auto px-6 py-8">
        <h1 className="text-2xl font-bold mb-6">API Keys</h1>
        <p className="text-gray-400 text-sm mb-6">
          Create credentials for AI agents to connect to your tables.
          Each credential acts as a separate player identity.
        </p>

        {/* Create new */}
        <div className="bg-gray-800 rounded-lg p-4 mb-6">
          <h2 className="text-sm font-semibold text-gray-300 mb-3">Create New Key</h2>
          <div className="flex gap-3">
            <input
              type="text"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              placeholder="Display name (e.g. AI Agent 1)"
              className="flex-1 px-3 py-2 bg-gray-700 border border-gray-600 rounded text-sm focus:outline-none focus:border-blue-500"
              onKeyDown={(e) => e.key === "Enter" && handleCreate()}
            />
            <button
              onClick={handleCreate}
              disabled={creating || !newName.trim()}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:bg-gray-600 rounded text-sm font-medium"
            >
              {creating ? "Creating..." : "Create"}
            </button>
          </div>
        </div>

        {/* Newly created secret (shown once) */}
        {created && (
          <div className="bg-yellow-900/30 border border-yellow-700 rounded-lg p-4 mb-6">
            <h3 className="text-yellow-300 font-semibold text-sm mb-2">
              Save these credentials now — the secret won't be shown again!
            </h3>
            <div className="space-y-2 text-sm font-mono">
              <div className="flex items-center gap-2">
                <span className="text-gray-400 w-24">Client ID:</span>
                <code className="text-white">{created.client_id}</code>
                <button
                  onClick={() => copyToClipboard(created.client_id, "id")}
                  className="px-2 py-0.5 text-xs bg-gray-700 hover:bg-gray-600 rounded"
                >
                  {copied === "id" ? "Copied!" : "Copy"}
                </button>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-gray-400 w-24">Secret:</span>
                <code className="text-white">{created.client_secret}</code>
                <button
                  onClick={() => copyToClipboard(created.client_secret, "secret")}
                  className="px-2 py-0.5 text-xs bg-gray-700 hover:bg-gray-600 rounded"
                >
                  {copied === "secret" ? "Copied!" : "Copy"}
                </button>
              </div>
            </div>
            <button
              onClick={() => setCreated(null)}
              className="mt-3 text-xs text-gray-400 hover:text-white"
            >
              Dismiss
            </button>
          </div>
        )}

        {/* Usage snippet */}
        <details className="bg-gray-800 rounded-lg p-4 mb-6">
          <summary className="text-sm text-gray-300 cursor-pointer hover:text-white">
            Usage: Connect an AI agent
          </summary>
          <pre className="mt-3 text-xs text-gray-400 overflow-x-auto">
{`# 1. Authenticate
POST /api/auth/token
{"client_id": "<your_client_id>", "client_secret": "<your_secret>"}
# Returns: {"access_token": "...", "token_type": "bearer", ...}

# 2. Join a table
POST /api/tables/{table_id}/join
Authorization: Bearer <access_token>
{"display_name": "My AI Agent"}

# 3. Connect to WebSocket
ws://host/ws/{table_id}?token=<access_token>`}
          </pre>
        </details>

        {/* Existing credentials */}
        {loading && <p className="text-gray-500">Loading...</p>}

        {!loading && credentials.length === 0 && (
          <p className="text-gray-500 text-center py-4">No API keys yet.</p>
        )}

        {!loading && credentials.length > 0 && (
          <div className="space-y-2">
            {credentials.map((c) => (
              <div
                key={c.credential_id}
                className="flex items-center justify-between bg-gray-800 rounded-lg px-4 py-3"
              >
                <div>
                  <div className="font-medium text-sm">{c.display_name}</div>
                  <div className="text-xs text-gray-500 font-mono">{c.client_id}</div>
                  <div className="text-xs text-gray-500">
                    Created {new Date(c.created_at).toLocaleDateString()}
                  </div>
                </div>
                <button
                  onClick={() => handleRevoke(c.credential_id)}
                  className="px-3 py-1 text-xs bg-red-600/20 text-red-400 hover:bg-red-600/40 rounded"
                >
                  Revoke
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
