import { useState, useEffect, useRef } from "react";
import { ActionType, ZoneKind } from "../../types/enums";
import type { ActionIntent, Zone } from "../../types/models";

interface Props {
  deckZone: Zone;
  zones: Zone[];
  seatIds: string[];
  sendAction: (intent: ActionIntent) => void;
  onClose: () => void;
}

export function DealPopover({
  deckZone,
  zones,
  seatIds,
  sendAction,
  onClose,
}: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const playerCount = seatIds.length || 1;
  const maxPerPlayer = Math.floor(deckZone.card_ids.length / playerCount);
  const [count, setCount] = useState(Math.min(maxPerPlayer, 5));

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        onClose();
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [onClose]);

  const handZoneIds = zones
    .filter((z) => z.kind === ZoneKind.HAND)
    .map((z) => z.zone_id);

  const totalCards = count * playerCount;

  const handleDeal = () => {
    if (count <= 0 || totalCards > deckZone.card_ids.length) return;

    const cardIds = deckZone.card_ids.slice(0, totalCards);

    sendAction({
      action_type: ActionType.DEAL_ROUND_ROBIN,
      card_ids: cardIds,
      source_zone_id: deckZone.zone_id,
      target_zone_ids: handZoneIds,
    });
    onClose();
  };

  return (
    <div
      ref={ref}
      className="absolute top-full left-0 mt-1 z-50 bg-gray-800 border border-gray-600 rounded-lg shadow-xl p-4 w-64"
    >
      <div className="text-sm font-medium mb-3">Deal Cards</div>

      <div className="space-y-3">
        <div>
          <label className="block text-xs text-gray-400 mb-1">
            Cards per player
          </label>
          <input
            type="number"
            min={1}
            max={maxPerPlayer}
            value={count}
            onChange={(e) => setCount(Math.max(1, parseInt(e.target.value) || 1))}
            className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-1.5 text-sm focus:border-blue-500 focus:outline-none"
            autoFocus
            onKeyDown={(e) => {
              if (e.key === "Enter") handleDeal();
              if (e.key === "Escape") onClose();
            }}
          />
        </div>

        <div className="text-xs text-gray-500">
          {totalCards} of {deckZone.card_ids.length} cards to{" "}
          {playerCount} player{playerCount !== 1 ? "s" : ""}
        </div>

        <button
          onClick={handleDeal}
          disabled={count <= 0 || totalCards > deckZone.card_ids.length}
          className="w-full px-3 py-1.5 rounded text-sm bg-blue-600 hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          Deal
        </button>
      </div>
    </div>
  );
}
