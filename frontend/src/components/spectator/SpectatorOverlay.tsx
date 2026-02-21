import { Link } from "react-router-dom";
import type { Seat, Zone } from "../../types/models";
import { ZoneKind } from "../../types/enums";

interface Props {
  seats: Seat[];
  zones: Zone[];
}

export function SpectatorOverlay({ seats, zones }: Props) {
  return (
    <div className="flex items-center gap-4 px-4 py-2 bg-yellow-900/30 border-b border-yellow-700/50 text-sm">
      <span className="bg-yellow-600/50 text-yellow-200 px-2 py-0.5 rounded text-xs font-medium">
        SPECTATING
      </span>
      <div className="flex gap-3 text-gray-300">
        {seats.map((s) => {
          const hand = zones.find(
            (z) => z.kind === ZoneKind.HAND && z.owner_seat_id === s.seat_id,
          );
          return (
            <span key={s.seat_id} className="text-xs">
              {s.display_name}: {hand?.card_ids.length ?? "?"} cards
            </span>
          );
        })}
      </div>
      <Link
        to="/lobby"
        className="ml-auto text-xs text-gray-400 hover:text-white"
      >
        Back to Lobby
      </Link>
    </div>
  );
}
