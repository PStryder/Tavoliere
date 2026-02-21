import type { Card, Zone } from "../../types/models";
import { CardView } from "./CardView";

interface Props {
  zone: Zone;
  cards: Record<string, Card>;
}

export function SeatOwnedZone({ zone, cards }: Props) {
  const zoneCards = zone.card_ids
    .map((id) => cards[id])
    .filter((c): c is Card => !!c);

  return (
    <div className="p-2 bg-gray-800/40 rounded border border-gray-700 min-h-[60px]">
      <div className="text-[10px] text-gray-500 mb-1 uppercase tracking-wide">
        {zone.label || zone.kind}
      </div>
      <div className="flex flex-wrap gap-0.5">
        {zoneCards.map((card) => (
          <CardView key={card.unique_id} card={card} faceUp={card.face_up} />
        ))}
        {zoneCards.length === 0 && (
          <span className="text-gray-600 text-xs">empty</span>
        )}
      </div>
    </div>
  );
}
