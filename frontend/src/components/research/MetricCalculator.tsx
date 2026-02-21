import { useState } from "react";
import { computeMetrics } from "../../api/research";
import type { SessionSPQAN } from "../../types/models";
import { MetricDisplay } from "./MetricDisplay";

const FAMILIES = ["ce", "rc", "ns", "ca", "ssc"] as const;

interface Props {
  selectedTableIds: Set<string>;
}

export function MetricCalculator({ selectedTableIds }: Props) {
  const [enabledFamilies, setEnabledFamilies] = useState<Set<string>>(new Set(FAMILIES));
  const [results, setResults] = useState<SessionSPQAN[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function toggleFamily(f: string) {
    setEnabledFamilies((prev) => {
      const next = new Set(prev);
      if (next.has(f)) next.delete(f); else next.add(f);
      return next;
    });
  }

  async function handleCompute() {
    if (selectedTableIds.size === 0) return;
    setLoading(true);
    setError(null);
    try {
      const families = enabledFamilies.size < FAMILIES.length
        ? Array.from(enabledFamilies)
        : undefined;
      const r = await computeMetrics(Array.from(selectedTableIds), families);
      setResults(r);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Computation failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-3 items-center">
        {FAMILIES.map((f) => (
          <label key={f} className="flex items-center gap-1 text-sm">
            <input type="checkbox" checked={enabledFamilies.has(f)}
              onChange={() => toggleFamily(f)} className="accent-blue-500" />
            <span className="uppercase text-gray-300">{f}</span>
          </label>
        ))}

        <button onClick={handleCompute} disabled={loading || selectedTableIds.size === 0}
          className="ml-4 px-4 py-1 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 rounded text-sm font-medium">
          {loading ? "Computing..." : `Compute (${selectedTableIds.size} session${selectedTableIds.size !== 1 ? "s" : ""})`}
        </button>
      </div>

      {error && <p className="text-red-400 text-sm">{error}</p>}

      {results.map((r) => (
        <div key={r.table_id} className="bg-gray-800/50 rounded-lg p-4 space-y-2">
          <div className="flex items-center justify-between text-xs text-gray-400">
            <span>Session: {r.session_id.slice(0, 8)}...</span>
            <span>{r.event_count} events | {(r.duration_ms / 1000).toFixed(1)}s</span>
          </div>
          <MetricDisplay seats={r.seats} />
        </div>
      ))}
    </div>
  );
}
