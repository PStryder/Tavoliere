import type { Seat, AckPosture } from "../../types/models";

interface Props {
  seats: Seat[];
  mySeatId: string;
  onUpdate: (posture: AckPosture) => void;
}

const POSTURE_KEYS: (keyof AckPosture)[] = [
  "move_card",
  "deal",
  "set_phase",
  "create_zone",
  "undo",
];

export function AckPosturePanel({ seats, mySeatId, onUpdate }: Props) {
  const mySeat = seats.find((s) => s.seat_id === mySeatId);
  if (!mySeat) return null;

  const posture = mySeat.ack_posture;

  function toggle(key: keyof AckPosture) {
    const updated = { ...posture, [key]: !posture[key] };
    onUpdate(updated);
  }

  return (
    <div className="flex items-center gap-3 px-4 py-1.5 border-t border-gray-700 bg-gray-800/60 text-xs">
      <span className="text-gray-500">Auto-ACK:</span>
      {POSTURE_KEYS.map((key) => (
        <label key={key} className="flex items-center gap-1 text-gray-400">
          <input
            type="checkbox"
            checked={posture[key]}
            onChange={() => toggle(key)}
            className="rounded bg-gray-700 border-gray-600 w-3 h-3"
          />
          {key.replace(/_/g, " ")}
        </label>
      ))}
    </div>
  );
}
