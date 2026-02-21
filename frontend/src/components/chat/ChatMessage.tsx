import type { ChatMessage as ChatMsg, Seat } from "../../types/models";
import { PlayerKind } from "../../types/enums";

interface Props {
  message: ChatMsg;
  seat?: Seat;
}

export function ChatMessage({ message, seat }: Props) {
  const time = new Date(message.timestamp).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  });

  return (
    <div className="px-3 py-1">
      <div className="flex items-baseline gap-2">
        <span className="text-xs font-medium text-blue-400">
          {seat?.display_name ?? message.seat_id.slice(-6)}
        </span>
        {seat?.player_kind === PlayerKind.AI && (
          <span className="text-[9px] bg-purple-600/50 text-purple-200 px-1 rounded">
            AI
          </span>
        )}
        <span className="text-[10px] text-gray-600">{time}</span>
      </div>
      <p className="text-sm text-gray-300">{message.text}</p>
    </div>
  );
}
