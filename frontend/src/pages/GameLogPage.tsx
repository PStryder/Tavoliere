import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import { Header } from "../components/layout/Header";
import { listGames } from "../api/history";
import type { TableMeta } from "../types/models";

type SortKey = "destroyed_at" | "display_name" | "deck_recipe";

export function GameLogPage() {
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();
  const [games, setGames] = useState<TableMeta[]>([]);
  const [loading, setLoading] = useState(true);
  const [sortKey, setSortKey] = useState<SortKey>("destroyed_at");
  const [sortAsc, setSortAsc] = useState(false);

  useEffect(() => {
    if (!isAuthenticated) {
      navigate("/");
      return;
    }
    listGames()
      .then(setGames)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [isAuthenticated, navigate]);

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortAsc(!sortAsc);
    } else {
      setSortKey(key);
      setSortAsc(key !== "destroyed_at");
    }
  };

  const sorted = [...games].sort((a, b) => {
    const va = String(a[sortKey] ?? "");
    const vb = String(b[sortKey] ?? "");
    const cmp = va.localeCompare(vb);
    return sortAsc ? cmp : -cmp;
  });

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      <Header />
      <div className="max-w-4xl mx-auto px-6 py-8">
        <h1 className="text-2xl font-bold mb-6">My Games</h1>

        {loading && <p className="text-gray-500">Loading...</p>}

        {!loading && games.length === 0 && (
          <p className="text-gray-500 text-center py-8">
            No completed games yet. Play some games first!
          </p>
        )}

        {!loading && games.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-gray-400 border-b border-gray-700">
                  <th
                    className="text-left py-2 px-3 cursor-pointer hover:text-white"
                    onClick={() => handleSort("destroyed_at")}
                  >
                    Date {sortKey === "destroyed_at" && (sortAsc ? "^" : "v")}
                  </th>
                  <th
                    className="text-left py-2 px-3 cursor-pointer hover:text-white"
                    onClick={() => handleSort("display_name")}
                  >
                    Name {sortKey === "display_name" && (sortAsc ? "^" : "v")}
                  </th>
                  <th
                    className="text-left py-2 px-3 cursor-pointer hover:text-white"
                    onClick={() => handleSort("deck_recipe")}
                  >
                    Deck {sortKey === "deck_recipe" && (sortAsc ? "^" : "v")}
                  </th>
                  <th className="text-center py-2 px-3">Players</th>
                  <th className="text-center py-2 px-3">Events</th>
                  <th className="text-center py-2 px-3">Research</th>
                  <th className="py-2 px-3"></th>
                </tr>
              </thead>
              <tbody>
                {sorted.map((g) => (
                  <tr
                    key={g.table_id}
                    className="border-b border-gray-800 hover:bg-gray-800/50 cursor-pointer"
                    onClick={() => navigate(`/replay/${g.table_id}`)}
                  >
                    <td className="py-2 px-3 text-gray-400">
                      {new Date(g.destroyed_at).toLocaleDateString()}
                    </td>
                    <td className="py-2 px-3 font-medium">{g.display_name}</td>
                    <td className="py-2 px-3 text-gray-400">
                      {g.deck_recipe.replace(/_/g, " ")}
                    </td>
                    <td className="py-2 px-3 text-center">{g.seats.length}</td>
                    <td className="py-2 px-3 text-center">{g.event_count}</td>
                    <td className="py-2 px-3 text-center">
                      {g.research_mode && (
                        <span className="text-xs bg-purple-600/30 text-purple-300 px-2 py-0.5 rounded">
                          research
                        </span>
                      )}
                    </td>
                    <td className="py-2 px-3 text-right">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          navigate(`/replay/${g.table_id}`);
                        }}
                        className="px-3 py-1 bg-blue-600 hover:bg-blue-500 rounded text-xs font-medium"
                      >
                        Replay
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
