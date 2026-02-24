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
        {zoneCards.length > 0 && (
          <span className="ml-1 text-gray-600">({zoneCards.length})</span>
        )}
      </div>
      {zoneCards.length > 0 ? (
        <div className="relative" style={{ height: 80, width: 56 }}>
          <div className="absolute top-0 left-0" style={{ zIndex: zoneCards.length }}>
            <CardView card={zoneCards[zoneCards.length - 1]} faceUp={zoneCards[zoneCards.length - 1].face_up} />
          </div>
          {(() => {
            const beneath = zoneCards.slice(0, -1).reverse();
            const showCount = Math.min(beneath.length, 4);
            const overflow = beneath.length - showCount;
            return (
              <>
                {beneath.slice(0, showCount).map((card, i) => (
                  <div
                    key={card.unique_id}
                    className="absolute left-0"
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
        <span className="text-gray-600 text-xs">empty</span>
      )}
    </div>
  );
}
