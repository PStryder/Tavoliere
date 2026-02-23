import { useState } from "react";
import { getResearchEvents, exportResearchEventsUrl } from "../../api/research";
import { getToken } from "../../api/client";
import type { ResearchEvent } from "../../types/models";

interface Props {
  availableTableIds: string[];
}

export function EventInspector({ availableTableIds }: Props) {
  const [tableId, setTableId] = useState(availableTableIds[0] ?? "");
  const [eventType, setEventType] = useState("");
  const [fromSeq, setFromSeq] = useState("");
  const [toSeq, setToSeq] = useState("");
  const [events, setEvents] = useState<ResearchEvent[]>([]);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function fetchEvents() {
    if (!tableId) return;
    setLoading(true);
    try {
      const result = await getResearchEvents(tableId, {
        from_seq: fromSeq ? Number(fromSeq) : undefined,
        to_seq: toSeq ? Number(toSeq) : undefined,
        event_type: eventType || undefined,
      });
      setEvents(result);
    } catch {
      setEvents([]);
    } finally {
      setLoading(false);
    }
  }

  function handleExport() {
    if (!tableId) return;
    const url = exportResearchEventsUrl(tableId);
    const token = getToken();
    // Open in new tab with auth via fetch + blob
    fetch(url, { headers: token ? { Authorization: `Bearer ${token}` } : {} })
      .then((r) => {
        if (!r.ok) throw new Error(`Export failed: ${r.status}`);
        return r.blob();
      })
      .then((blob) => {
        const a = document.createElement("a");
        a.href = URL.createObjectURL(blob);
        a.download = `${tableId}.research.ndjson`;
        a.click();
        URL.revokeObjectURL(a.href);
      })
      .catch((err) => {
        console.error("Export failed:", err);
      });
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-3 items-end">
        <label className="text-xs text-gray-400">
          Session
          <select value={tableId} onChange={(e) => setTableId(e.target.value)}
            className="block mt-1 bg-gray-800 border border-gray-700 rounded px-2 py-1 text-sm text-white w-40">
            {availableTableIds.map((id) => (
              <option key={id} value={id}>{id.slice(0, 8)}...</option>
            ))}
          </select>
        </label>
        <label className="text-xs text-gray-400">
          Event Type
          <input type="text" value={eventType} onChange={(e) => setEventType(e.target.value)}
            placeholder="e.g. ACTION_COMMITTED"
            className="block mt-1 bg-gray-800 border border-gray-700 rounded px-2 py-1 text-sm text-white w-40" />
        </label>
        <label className="text-xs text-gray-400">
          From Seq
          <input type="number" value={fromSeq} onChange={(e) => setFromSeq(e.target.value)}
            className="block mt-1 bg-gray-800 border border-gray-700 rounded px-2 py-1 text-sm text-white w-20" />
        </label>
        <label className="text-xs text-gray-400">
          To Seq
          <input type="number" value={toSeq} onChange={(e) => setToSeq(e.target.value)}
            className="block mt-1 bg-gray-800 border border-gray-700 rounded px-2 py-1 text-sm text-white w-20" />
        </label>
        <button onClick={fetchEvents} disabled={loading || !tableId}
          className="px-3 py-1 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 rounded text-sm font-medium">
          {loading ? "Loading..." : "Load"}
        </button>
        <button onClick={handleExport} disabled={!tableId}
          className="px-3 py-1 bg-gray-700 hover:bg-gray-600 disabled:opacity-50 rounded text-sm font-medium">
          Export NDJSON
        </button>
      </div>

      {events.length > 0 && (
        <div className="max-h-[500px] overflow-y-auto space-y-1">
          {events.map((ev) => (
            <div key={ev.event_id} className="bg-gray-800/50 rounded p-2">
              <div
                className="flex items-center justify-between cursor-pointer text-sm"
                onClick={() => setExpandedId(expandedId === ev.event_id ? null : ev.event_id)}
              >
                <span className="font-mono text-xs text-gray-300">
                  #{ev.server_sequence_number} {ev.event_type}
                </span>
                <span className="text-xs text-gray-500">
                  {ev.phase_label || "--"} | seq {ev.gameplay_seq}
                </span>
              </div>
              {expandedId === ev.event_id && (
                <pre className="mt-2 text-xs text-gray-400 bg-gray-900 rounded p-2 overflow-x-auto max-h-48">
                  {JSON.stringify(ev, null, 2)}
                </pre>
              )}
            </div>
          ))}
        </div>
      )}

      {!loading && events.length === 0 && tableId && (
        <p className="text-gray-500 text-sm">No events loaded. Click Load to fetch.</p>
      )}
    </div>
  );
}
