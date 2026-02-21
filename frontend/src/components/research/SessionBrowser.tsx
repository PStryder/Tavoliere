import { useEffect, useState } from "react";
import { listResearchSessions } from "../../api/research";
import type { ResearchSession } from "../../types/models";

interface Props {
  selectedIds: Set<string>;
  onToggle: (tableId: string) => void;
}

export function SessionBrowser({ selectedIds, onToggle }: Props) {
  const [sessions, setSessions] = useState<ResearchSession[]>([]);
  const [loading, setLoading] = useState(true);
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [deckRecipe, setDeckRecipe] = useState("");
  const [hasAi, setHasAi] = useState<"" | "true" | "false">("");
  const [sortField, setSortField] = useState<"destroyed_at" | "event_count">("destroyed_at");
  const [sortAsc, setSortAsc] = useState(false);

  function fetchSessions() {
    setLoading(true);
    listResearchSessions({
      date_from: dateFrom || undefined,
      date_to: dateTo || undefined,
      deck_recipe: deckRecipe || undefined,
      has_ai: hasAi === "" ? undefined : hasAi === "true",
    })
      .then(setSessions)
      .catch(() => setSessions([]))
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    fetchSessions();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const sorted = [...sessions].sort((a, b) => {
    const av = sortField === "destroyed_at" ? a.destroyed_at : a.event_count;
    const bv = sortField === "destroyed_at" ? b.destroyed_at : b.event_count;
    if (av < bv) return sortAsc ? -1 : 1;
    if (av > bv) return sortAsc ? 1 : -1;
    return 0;
  });

  function toggleSort(field: typeof sortField) {
    if (sortField === field) setSortAsc(!sortAsc);
    else { setSortField(field); setSortAsc(false); }
  }

  return (
    <div className="space-y-4">
      {/* Filters */}
      <div className="flex flex-wrap gap-3 items-end">
        <label className="text-xs text-gray-400">
          From
          <input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)}
            className="block mt-1 bg-gray-800 border border-gray-700 rounded px-2 py-1 text-sm text-white" />
        </label>
        <label className="text-xs text-gray-400">
          To
          <input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)}
            className="block mt-1 bg-gray-800 border border-gray-700 rounded px-2 py-1 text-sm text-white" />
        </label>
        <label className="text-xs text-gray-400">
          Deck
          <input type="text" value={deckRecipe} onChange={(e) => setDeckRecipe(e.target.value)}
            placeholder="e.g. standard_52"
            className="block mt-1 bg-gray-800 border border-gray-700 rounded px-2 py-1 text-sm text-white w-32" />
        </label>
        <label className="text-xs text-gray-400">
          AI
          <select value={hasAi} onChange={(e) => setHasAi(e.target.value as "" | "true" | "false")}
            className="block mt-1 bg-gray-800 border border-gray-700 rounded px-2 py-1 text-sm text-white">
            <option value="">Any</option>
            <option value="true">With AI</option>
            <option value="false">No AI</option>
          </select>
        </label>
        <button onClick={fetchSessions}
          className="px-3 py-1 bg-blue-600 hover:bg-blue-500 rounded text-sm font-medium">
          Filter
        </button>
      </div>

      {/* Table */}
      {loading ? (
        <p className="text-gray-500 text-sm">Loading sessions...</p>
      ) : sorted.length === 0 ? (
        <p className="text-gray-500 text-sm">No research sessions found.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm text-left">
            <thead className="text-xs text-gray-400 border-b border-gray-700">
              <tr>
                <th className="py-2 pr-3 w-8"></th>
                <th className="py-2 pr-3">Name</th>
                <th className="py-2 pr-3">Deck</th>
                <th className="py-2 pr-3">Seats</th>
                <th className="py-2 pr-3 cursor-pointer hover:text-white" onClick={() => toggleSort("event_count")}>
                  Events {sortField === "event_count" ? (sortAsc ? "^" : "v") : ""}
                </th>
                <th className="py-2 pr-3 cursor-pointer hover:text-white" onClick={() => toggleSort("destroyed_at")}>
                  Destroyed {sortField === "destroyed_at" ? (sortAsc ? "^" : "v") : ""}
                </th>
              </tr>
            </thead>
            <tbody>
              {sorted.map((s) => (
                <tr key={s.table_id} className="border-b border-gray-800 hover:bg-gray-800/50">
                  <td className="py-2 pr-3">
                    <input type="checkbox" checked={selectedIds.has(s.table_id)}
                      onChange={() => onToggle(s.table_id)}
                      className="accent-blue-500" />
                  </td>
                  <td className="py-2 pr-3">{s.display_name}</td>
                  <td className="py-2 pr-3">{s.deck_recipe}</td>
                  <td className="py-2 pr-3">{s.seats.length}</td>
                  <td className="py-2 pr-3">{s.event_count}</td>
                  <td className="py-2 pr-3 text-xs text-gray-400">{s.destroyed_at?.slice(0, 19)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
