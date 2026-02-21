import { useEffect, useState } from "react";
import { listPrincipals, deletePrincipal } from "../../api/admin";
import type { PrincipalInfo } from "../../types/models";

export function UserManager() {
  const [principals, setPrincipals] = useState<PrincipalInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");

  useEffect(() => {
    load();
  }, []);

  function load() {
    listPrincipals()
      .then(setPrincipals)
      .catch(() => {})
      .finally(() => setLoading(false));
  }

  async function handleDelete(id: string, name: string) {
    if (!confirm(`Delete principal "${name}"? This revokes all their credentials.`)) return;
    try {
      await deletePrincipal(id);
      load();
    } catch {
      /* empty */
    }
  }

  const filtered = principals.filter(
    (p) =>
      p.display_name.toLowerCase().includes(search.toLowerCase()) ||
      p.identity_id.includes(search),
  );

  if (loading) return <p className="text-gray-500 py-4">Loading...</p>;

  return (
    <div>
      <input
        type="text"
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        placeholder="Search by name or ID..."
        className="w-full mb-4 px-3 py-2 bg-gray-700 border border-gray-600 rounded text-sm focus:outline-none focus:border-blue-500"
      />

      {filtered.length === 0 && (
        <p className="text-gray-500 text-center py-4">No principals found.</p>
      )}

      <div className="space-y-2">
        {filtered.map((p) => (
          <div
            key={p.identity_id}
            className="flex items-center justify-between bg-gray-800/50 rounded-lg px-4 py-3"
          >
            <div>
              <div className="flex items-center gap-2">
                <span className="font-medium text-sm">{p.display_name}</span>
                {p.is_admin && (
                  <span className="text-xs bg-purple-600/30 text-purple-300 px-1.5 py-0.5 rounded">
                    admin
                  </span>
                )}
              </div>
              <div className="text-xs text-gray-500 font-mono">{p.identity_id}</div>
              <div className="text-xs text-gray-500">
                {p.credential_count} key{p.credential_count !== 1 ? "s" : ""} · Created{" "}
                {new Date(p.created_at).toLocaleDateString()}
              </div>
            </div>
            {!p.is_admin && (
              <button
                onClick={() => handleDelete(p.identity_id, p.display_name)}
                className="px-3 py-1 text-xs bg-red-600/20 text-red-400 hover:bg-red-600/40 rounded"
              >
                Delete
              </button>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
