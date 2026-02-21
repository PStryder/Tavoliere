import type { Seat } from "../../types/models";
import { Presence, PlayerKind } from "../../types/enums";

interface Props {
  seat: Seat;
  isMe?: boolean;
  isHost?: boolean;
}

export function SeatDisplay({ seat, isMe = false, isHost = false }: Props) {
  const presenceColor =
    seat.presence === Presence.ACTIVE
      ? "bg-green-500"
      : seat.presence === Presence.DISCONNECTED
        ? "bg-yellow-500"
        : "bg-gray-500";

  return (
    <div
      className={`flex items-center gap-2 px-3 py-1.5 rounded-lg ${
        isMe ? "bg-blue-900/40 border border-blue-700" : "bg-gray-800/60"
      }`}
    >
      <div className={`w-2 h-2 rounded-full ${presenceColor}`} />
      <span className="text-sm font-medium truncate max-w-[120px]">
        {seat.display_name}
      </span>
      {seat.player_kind === PlayerKind.AI && (
        <span className="text-[10px] bg-purple-600/50 text-purple-200 px-1.5 rounded">
          AI
        </span>
      )}
      {isHost && (
        <span className="text-[10px] bg-yellow-600/50 text-yellow-200 px-1.5 rounded">
          host
        </span>
      )}
    </div>
  );
}
