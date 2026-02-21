import { useEffect, useState } from "react";
import { listAllCredentials, adminRevokeCredential } from "../../api/admin";
import type { CredentialPublic } from "../../types/models";

export function ApiKeyAdmin() {
  const [credentials, setCredentials] = useState<CredentialPublic[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("");

  useEffect(() => {
    load();
  }, []);

  function load() {
    listAllCredentials()
      .then(setCredentials)
      .catch(() => {})
      .finally(() => setLoading(false));
  }

  async function handleRevoke(id: string, name: string) {
    if (!confirm(`Force-revoke credential "${name}"?`)) return;
    try {
      await adminRevokeCredential(id);
      load();
    } catch {
      /* empty */
    }
  }

  const filtered = credentials.filter(
    (c) =>
      c.display_name.toLowerCase().includes(filter.toLowerCase()) ||
      c.client_id.includes(filter),
  );

  if (loading) return <p className="text-gray-500 py-4">Loading...</p>;

  return (
    <div>
      <input
        type="text"
        value={filter}
        onChange={(e) => setFilter(e.target.value)}
        placeholder="Filter by name or client ID..."
        className="w-full mb-4 px-3 py-2 bg-gray-700 border border-gray-600 rounded text-sm focus:outline-none focus:border-blue-500"
      />

      {filtered.length === 0 && (
        <p className="text-gray-500 text-center py-4">No credentials found.</p>
      )}

      <div className="space-y-2">
        {filtered.map((c) => (
          <div
            key={c.credential_id}
            className="flex items-center justify-between bg-gray-800/50 rounded-lg px-4 py-3"
          >
            <div>
              <div className="flex items-center gap-2">
                <span className="font-medium text-sm">{c.display_name}</span>
                <span className="text-xs text-gray-500">{c.player_kind}</span>
              </div>
              <div className="text-xs text-gray-500 font-mono">{c.client_id}</div>
              <div className="text-xs text-gray-500">
                Created {new Date(c.created_at).toLocaleDateString()}
              </div>
            </div>
            <button
              onClick={() => handleRevoke(c.credential_id, c.display_name)}
              className="px-3 py-1 text-xs bg-red-600/20 text-red-400 hover:bg-red-600/40 rounded"
            >
              Revoke
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
