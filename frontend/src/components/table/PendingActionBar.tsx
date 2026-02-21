import { useState } from "react";
import type { PendingAction, Seat } from "../../types/models";
import { DisputeReason } from "../../types/enums";

interface Props {
  pendingActions: PendingAction[];
  mySeatId: string | null;
  seats: Seat[];
  onAck: (actionId: string) => void;
  onNack: (actionId: string, reason?: DisputeReason, reasonText?: string) => void;
}

export function PendingActionBar({
  pendingActions,
  mySeatId,
  seats,
  onAck,
  onNack,
}: Props) {
  const [nackReason, setNackReason] = useState<DisputeReason>(
    DisputeReason.RULES,
  );

  const seatName = (id: string) =>
    seats.find((s) => s.seat_id === id)?.display_name ?? id.slice(-6);

  return (
    <div className="border-t border-gray-700 bg-gray-800/80 px-4 py-2 space-y-2">
      {pendingActions.map((pa) => {
        const isProposer = pa.proposer_seat_id === mySeatId;
        const alreadyAcked = pa.received_acks.includes(mySeatId ?? "");
        const ackProgress = `${pa.received_acks.length}/${pa.required_acks.length}`;

        return (
          <div
            key={pa.action_id}
            className="flex items-center gap-3 text-sm"
          >
            <span className="text-gray-400">
              {seatName(pa.proposer_seat_id)} wants to{" "}
              <span className="text-white font-medium">
                {pa.intent.action_type}
              </span>
            </span>
            <span className="text-gray-500">({ackProgress} acked)</span>

            {!isProposer && !alreadyAcked && (
              <div className="flex items-center gap-2 ml-auto">
                <select
                  value={nackReason}
                  onChange={(e) =>
                    setNackReason(e.target.value as DisputeReason)
                  }
                  className="text-xs bg-gray-700 border border-gray-600 rounded px-1 py-0.5 text-gray-300"
                >
                  {Object.values(DisputeReason).map((r) => (
                    <option key={r} value={r}>
                      {r}
                    </option>
                  ))}
                </select>
                <button
                  onClick={() => onNack(pa.action_id, nackReason)}
                  className="px-3 py-1 bg-red-600 hover:bg-red-500 rounded text-xs font-medium"
                >
                  NACK
                </button>
                <button
                  onClick={() => onAck(pa.action_id)}
                  className="px-3 py-1 bg-green-600 hover:bg-green-500 rounded text-xs font-medium"
                >
                  ACK
                </button>
              </div>
            )}

            {alreadyAcked && (
              <span className="text-green-400 text-xs ml-auto">Acked</span>
            )}
          </div>
        );
      })}
    </div>
  );
}
