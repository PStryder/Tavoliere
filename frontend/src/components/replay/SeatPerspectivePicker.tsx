import type { Seat } from "../../types/models";

interface Props {
  seats: Seat[];
  activePerspective: string;
  onSelect: (perspective: string) => void;
}

export function SeatPerspectivePicker({ seats, activePerspective, onSelect }: Props) {
  return (
    <div className="flex gap-1 px-4 py-2 bg-gray-800/50 border-b border-gray-700">
      <span className="text-xs text-gray-500 mr-2 self-center">Perspective:</span>
      <button
        onClick={() => onSelect("__observer__")}
        className={`px-2 py-1 text-xs rounded ${
          activePerspective === "__observer__"
            ? "bg-blue-600 text-white"
            : "bg-gray-700 text-gray-400 hover:bg-gray-600"
        }`}
      >
        Observer
      </button>
      {seats.map((s) => (
        <button
          key={s.seat_id}
          onClick={() => onSelect(s.seat_id)}
          className={`px-2 py-1 text-xs rounded ${
            activePerspective === s.seat_id
              ? "bg-blue-600 text-white"
              : "bg-gray-700 text-gray-400 hover:bg-gray-600"
          }`}
        >
          {s.display_name}
        </button>
      ))}
    </div>
  );
}
