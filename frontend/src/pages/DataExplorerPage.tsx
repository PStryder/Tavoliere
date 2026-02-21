import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import { Header } from "../components/layout/Header";
import { SessionBrowser } from "../components/research/SessionBrowser";
import { MetricCalculator } from "../components/research/MetricCalculator";
import { EventInspector } from "../components/research/EventInspector";

type Tab = "sessions" | "metrics" | "events";

export function DataExplorerPage() {
  const { isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<Tab>("sessions");
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());

  if (!isAuthenticated) {
    navigate("/");
    return null;
  }

  function toggleSelection(tableId: string) {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(tableId)) next.delete(tableId); else next.add(tableId);
      return next;
    });
  }

  const tabs: { key: Tab; label: string }[] = [
    { key: "sessions", label: "Sessions" },
    { key: "metrics", label: "Metrics" },
    { key: "events", label: "Events" },
  ];

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      <Header />
      <div className="max-w-5xl mx-auto px-6 py-8">
        <h1 className="text-2xl font-bold mb-6">Data Explorer</h1>

        {/* Tab bar */}
        <div className="flex gap-1 mb-6 border-b border-gray-700">
          {tabs.map((t) => (
            <button
              key={t.key}
              onClick={() => setActiveTab(t.key)}
              className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px ${
                activeTab === t.key
                  ? "border-blue-500 text-white"
                  : "border-transparent text-gray-400 hover:text-white"
              }`}
            >
              {t.label}
              {t.key === "sessions" && selectedIds.size > 0 && (
                <span className="ml-1 text-xs bg-blue-600 rounded-full px-1.5">{selectedIds.size}</span>
              )}
            </button>
          ))}
        </div>

        {/* Tab content */}
        {activeTab === "sessions" && (
          <SessionBrowser selectedIds={selectedIds} onToggle={toggleSelection} />
        )}
        {activeTab === "metrics" && (
          <MetricCalculator selectedTableIds={selectedIds} />
        )}
        {activeTab === "events" && (
          <EventInspector availableTableIds={Array.from(selectedIds)} />
        )}
      </div>
    </div>
  );
}
