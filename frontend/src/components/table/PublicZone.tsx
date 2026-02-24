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
        {zoneCards.length > 0 && (
          <span className="ml-1 text-gray-600">({zoneCards.length})</span>
        )}
      </div>
      {zoneCards.length > 0 ? (
        <div className="relative" style={{ height: 80, width: 56 }}>
          {/* Top card shown fully */}
          <div className="absolute top-0 left-0" style={{ zIndex: zoneCards.length }}>
            <CardView card={zoneCards[zoneCards.length - 1]} faceUp={zoneCards[zoneCards.length - 1].face_up} />
          </div>
          {/* Slivers beneath: show up to 4, with +N badge if more */}
          {(() => {
            const beneath = zoneCards.slice(0, -1).reverse();
            const showCount = Math.min(beneath.length, 4);
            const overflow = beneath.length - showCount;
            return (
              <>
                {beneath.slice(0, showCount).map((card, i) => (
                  <div
                    key={card.unique_id}
                    className="absolute left-0 flex items-center"
                    style={{ top: 0, zIndex: zoneCards.length - 1 - i, transform: `translateY(${(i + 1) * -4}px) translateX(${(i + 1) * 2}px)` }}
                  >
                    <div className="w-14 h-20 rounded-md bg-gray-700 border border-gray-600 opacity-60" />
                  </div>
                ))}
                {overflow > 0 && (
                  <div
                    className="absolute -top-2 -right-2 bg-gray-600 text-gray-200 text-[10px] font-bold rounded-full w-5 h-5 flex items-center justify-center"
                    style={{ zIndex: zoneCards.length + 1 }}
                  >
                    +{overflow}
                  </div>
                )}
              </>
            );
          })()}
        </div>
      ) : (
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
