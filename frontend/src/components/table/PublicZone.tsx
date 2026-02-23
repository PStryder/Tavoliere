import { useDroppable } from "@dnd-kit/core";
import type { Card, Zone } from "../../types/models";
import { ZoneKind } from "../../types/enums";
import { CardView } from "./CardView";
import { DeckPile } from "./DeckPile";

interface Props {
  zone: Zone;
  cards: Record<string, Card>;
  onDeckClick?: () => void;
}

export function PublicZone({ zone, cards, onDeckClick }: Props) {
  const { setNodeRef, isOver } = useDroppable({
    id: zone.zone_id,
    data: { zone },
  });

  if (zone.kind === ZoneKind.DECK) {
    return <DeckPile zone={zone} onClick={onDeckClick} />;
  }

  const zoneCards = zone.card_ids
    .map((id) => cards[id])
    .filter((c): c is Card => !!c);

  return (
    <div
      ref={setNodeRef}
      className={`flex flex-wrap gap-1 p-3 rounded-lg min-h-[96px] min-w-[80px] border-2 border-dashed transition-all ${
        isOver
          ? "border-blue-400 bg-blue-900/30 scale-[1.02] shadow-lg shadow-blue-900/20"
          : "border-gray-600 bg-gray-800/30 hover:border-gray-500"
      }`}
    >
      <div className="w-full text-xs text-gray-500 mb-1">
        {zone.label || zone.kind}
      </div>
      {zoneCards.map((card) => (
        <CardView key={card.unique_id} card={card} faceUp={card.face_up} />
      ))}
      {zoneCards.length === 0 && (
        <span
          className={`text-xs self-center ${
            isOver ? "text-blue-400" : "text-gray-600"
          }`}
        >
          {isOver ? "Drop here" : "Drop cards here"}
        </span>
      )}
    </div>
  );
}
