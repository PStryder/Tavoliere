import { useEffect, useState } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import { getSummary } from "../api/history";
import type { GameSummary } from "../types/models";
import { Header } from "../components/layout/Header";
import { SPQANSummary } from "../components/research/SPQANSummary";

export function PostGameSummary() {
  const { tableId } = useParams<{ tableId: string }>();
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();
  const [summary, setSummary] = useState<GameSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isAuthenticated) {
      navigate("/");
      return;
    }
    if (!tableId) return;
    getSummary(tableId)
      .then(setSummary)
      .catch((err) => setError(err.message ?? "Failed to load summary"))
      .finally(() => setLoading(false));
  }, [isAuthenticated, navigate, tableId]);

  if (!tableId) return null;

  function formatDuration(seconds: number): string {
    const m = Math.floor(seconds / 60);
    const s = Math.round(seconds % 60);
    return m > 0 ? `${m}m ${s}s` : `${s}s`;
  }

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      <Header />
      <div className="max-w-lg mx-auto px-6 py-12">
        {loading && <p className="text-gray-500 text-center">Loading...</p>}

        {error && (
          <div className="text-center">
            <p className="text-red-400 mb-4">{error}</p>
            <Link to="/lobby" className="text-blue-400 hover:underline">
              Return to Lobby
            </Link>
          </div>
        )}

        {summary && (
          <div className="space-y-6">
            <div className="text-center">
              <h1 className="text-2xl font-bold mb-1">{summary.display_name}</h1>
              <p className="text-gray-400 text-sm">Game Summary</p>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <StatCard label="Duration" value={formatDuration(summary.duration_s)} />
              <StatCard label="Total Events" value={String(summary.total_events)} />
              <StatCard label="Actions" value={String(summary.total_actions)} />
              <StatCard label="Disputes" value={String(summary.total_disputes)} />
              <StatCard label="Undos" value={String(summary.total_undos)} />
              <StatCard
                label="Deck"
                value={summary.deck_recipe.replace(/_/g, " ")}
              />
            </div>

            {summary.research_mode && <SPQANSummary tableId={tableId!} />}

            {/* Players */}
            <div className="bg-gray-800 rounded-lg p-4">
              <h2 className="text-sm font-medium text-gray-400 mb-2">Players</h2>
              <div className="space-y-1">
                {summary.seats.map((s) => (
                  <div key={s.seat_id} className="text-sm">
                    {s.display_name}
                  </div>
                ))}
              </div>
            </div>

            {/* Actions */}
            <div className="flex gap-3 justify-center">
              <Link
                to={`/replay/${tableId}`}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-500 rounded font-medium text-sm"
              >
                Watch Replay
              </Link>
              <Link
                to="/lobby"
                className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded font-medium text-sm"
              >
                Return to Lobby
              </Link>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-gray-800 rounded-lg p-3 text-center">
      <div className="text-lg font-bold">{value}</div>
      <div className="text-xs text-gray-400">{label}</div>
    </div>
  );
}
