import { useEffect, useState } from "react";
import { computeMetrics } from "../../api/research";
import type { SessionSPQAN } from "../../types/models";
import { MetricDisplay } from "./MetricDisplay";

export function SPQANSummary({ tableId }: { tableId: string }) {
  const [spqan, setSpqan] = useState<SessionSPQAN | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    computeMetrics([tableId])
      .then((results) => {
        if (results.length > 0) setSpqan(results[0]);
      })
      .catch((err) => setError(err.message ?? "Failed to compute metrics"))
      .finally(() => setLoading(false));
  }, [tableId]);

  if (loading) return <p className="text-gray-500 text-sm py-2">Computing SPQ-AN...</p>;
  if (error) return <p className="text-red-400 text-sm py-2">{error}</p>;
  if (!spqan || spqan.seats.length === 0) return null;

  return (
    <div className="bg-gray-800 rounded-lg p-4">
      <h2 className="text-sm font-medium text-gray-400 mb-3">SPQ-AN Metrics</h2>
      <MetricDisplay seats={spqan.seats} />
    </div>
  );
}
