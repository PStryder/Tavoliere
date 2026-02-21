import type { SeatSPQAN } from "../../types/models";

function fmt(v: number | null | undefined, decimals = 1): string {
  if (v === null || v === undefined) return "--";
  return v.toFixed(decimals);
}

function pct(v: number): string {
  return (v * 100).toFixed(1) + "%";
}

export function MetricDisplay({ seats }: { seats: SeatSPQAN[] }) {
  if (seats.length === 0) return <p className="text-gray-500 text-sm">No seat data.</p>;

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm text-left">
        <thead className="text-xs text-gray-400 border-b border-gray-700">
          <tr>
            <th className="py-2 pr-3">Seat</th>
            <th className="py-2 pr-3">Type</th>
            {/* CE */}
            <th className="py-2 pr-3" title="Mean Ack Latency (ms)">Ack Lat</th>
            <th className="py-2 pr-3" title="Dispute Density">Disp Den</th>
            <th className="py-2 pr-3" title="Rollback Rate">Rollback</th>
            {/* RC */}
            <th className="py-2 pr-3" title="Mean Resolution Latency (ms)">Res Lat</th>
            <th className="py-2 pr-3" title="Chat per Dispute">Chat/Disp</th>
            {/* NS */}
            <th className="py-2 pr-3" title="Auto-Ack Adoption">AA Adopt</th>
            <th className="py-2 pr-3" title="Phase Label Diversity">Phases</th>
            {/* CA */}
            <th className="py-2 pr-3" title="Mean Message Length">Msg Len</th>
            <th className="py-2 pr-3" title="Resolution Related Chat Ratio">Res Chat</th>
            {/* SSC */}
            <th className="py-2 pr-3" title="Dispute Initiation Rate">Init Rate</th>
            <th className="py-2 pr-3" title="Dispute Clustering">Cluster</th>
          </tr>
        </thead>
        <tbody>
          {seats.map((s) => (
            <tr key={s.seat_id} className="border-b border-gray-800">
              <td className="py-2 pr-3 font-mono text-xs">{s.pseudonym_id}</td>
              <td className="py-2 pr-3">{s.seat_type}</td>
              <td className="py-2 pr-3">{fmt(s.ce.mean_ack_latency_ms, 0)}</td>
              <td className="py-2 pr-3">{pct(s.ce.dispute_density)}</td>
              <td className="py-2 pr-3">{pct(s.ce.rollback_rate)}</td>
              <td className="py-2 pr-3">{fmt(s.rc.mean_resolution_latency_ms, 0)}</td>
              <td className="py-2 pr-3">{fmt(s.rc.mean_chat_per_dispute)}</td>
              <td className="py-2 pr-3">{pct(s.ns.auto_ack_adoption_rate)}</td>
              <td className="py-2 pr-3">{s.ns.phase_label_diversity}</td>
              <td className="py-2 pr-3">{fmt(s.ca.mean_message_length_chars, 0)}</td>
              <td className="py-2 pr-3">{pct(s.ca.resolution_related_chat_ratio)}</td>
              <td className="py-2 pr-3">{pct(s.ssc.dispute_initiation_rate)}</td>
              <td className="py-2 pr-3">{pct(s.ssc.dispute_clustering_score)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
