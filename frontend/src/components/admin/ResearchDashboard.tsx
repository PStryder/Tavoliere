import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getResearchHealth } from "../../api/admin";
import type { ResearchHealth } from "../../types/models";

interface ResearchHealthWithConsent extends ResearchHealth {
  consent_distribution?: Record<string, number>;
}

export function ResearchDashboard() {
  const [health, setHealth] = useState<ResearchHealthWithConsent | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getResearchHealth()
      .then((data) => setHealth(data as ResearchHealthWithConsent))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p className="text-gray-500 py-4">Loading...</p>;
  if (!health) return <p className="text-gray-500 py-4">Failed to load metrics.</p>;

  const metrics = [
    { label: "Active Tables", value: health.active_tables },
    { label: "Active Research Tables", value: health.active_research_tables },
    { label: "Persisted Sessions", value: health.persisted_sessions },
    { label: "Total Persisted Events", value: health.total_persisted_events },
  ];

  const consentDist = health.consent_distribution ?? {};
  const hasConsent = Object.keys(consentDist).length > 0;

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        {metrics.map((m) => (
          <div key={m.label} className="bg-gray-800/50 rounded-lg p-4 text-center">
            <div className="text-2xl font-bold text-white">{m.value}</div>
            <div className="text-xs text-gray-500 mt-1">{m.label}</div>
          </div>
        ))}
      </div>

      {hasConsent && (
        <div className="bg-gray-800/50 rounded-lg p-4">
          <h3 className="text-sm font-medium text-gray-400 mb-2">Consent Distribution</h3>
          <div className="grid grid-cols-2 gap-2">
            {Object.entries(consentDist).map(([tier, count]) => (
              <div key={tier} className="flex justify-between text-sm">
                <span className="text-gray-300">{tier.replace(/_/g, " ")}</span>
                <span className="text-white font-medium">{count}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      <Link
        to="/research/explorer"
        className="inline-block px-4 py-2 bg-blue-600 hover:bg-blue-500 rounded text-sm font-medium"
      >
        Open Data Explorer
      </Link>
    </div>
  );
}
