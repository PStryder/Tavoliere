import { useState, useEffect } from "react";
import {
  SortableContext,
  horizontalListSortingStrategy,
  useSortable,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import type { Card, Zone } from "../../types/models";
import { Suit } from "../../types/enums";

interface Props {
  zone: Zone;
  cards: Record<string, Card>;
  onReorder?: (newOrder: string[]) => void;
  onCardSelect?: (cardId: string) => void;
  selectedCards?: Set<string>;
}

const SUIT_SYMBOLS: Record<string, string> = {
  [Suit.HEARTS]: "\u2665",
  [Suit.DIAMONDS]: "\u2666",
  [Suit.CLUBS]: "\u2663",
  [Suit.SPADES]: "\u2660",
};

const SUIT_COLORS: Record<string, string> = {
  [Suit.HEARTS]: "text-red-500",
  [Suit.DIAMONDS]: "text-red-500",
  [Suit.CLUBS]: "text-white",
  [Suit.SPADES]: "text-white",
};

const EMPTY_SET = new Set<string>();

function SortableCard({
  card,
  zoneId,
  selected,
  onClick,
}: {
  card: Card;
  zoneId: string;
  selected: boolean;
  onClick: () => void;
}) {
  const { attributes, listeners, setNodeRef, transform, transition } =
    useSortable({ id: card.unique_id, data: { zone: zoneId } });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  const suitSymbol = SUIT_SYMBOLS[card.suit] ?? "?";
  const suitColor = SUIT_COLORS[card.suit] ?? "text-white";

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...attributes}
      {...listeners}
      className={`w-14 h-20 rounded-md bg-white border-2 flex flex-col items-center justify-center select-none cursor-grab active:cursor-grabbing ${
        selected ? "border-blue-400 ring-2 ring-blue-400" : "border-gray-300"
      }`}
      onClick={onClick}
    >
      <span className={`text-sm font-bold leading-none ${suitColor}`}>
        {card.rank}
      </span>
      <span className={`text-lg leading-none ${suitColor}`}>{suitSymbol}</span>
      <span className="text-[8px] text-gray-400 mt-0.5">
        {card.unique_id.slice(-4)}
      </span>
    </div>
  );
}

export function HandZone({
  zone,
  cards,
  onCardSelect,
  selectedCards = EMPTY_SET,
}: Props) {
  const [cardOrder, setCardOrder] = useState<string[]>(zone.card_ids);

  // Sync local order when zone cards change (added/removed cards, or server reorder)
  useEffect(() => {
    const zoneSet = new Set(zone.card_ids);
    const localSet = new Set(cardOrder);

    // If the card membership changed (cards added or removed), adopt server order
    const sameMembers =
      zoneSet.size === localSet.size &&
      zone.card_ids.every((id) => localSet.has(id));

    if (!sameMembers) {
      setCardOrder(zone.card_ids);
    }
  }, [zone.card_ids]); // eslint-disable-line react-hooks/exhaustive-deps

  // Expose handleReorder for the outer DndContext to call via onReorder
  // The outer DndContext detects same-zone reorder and calls onReorder directly

  return (
    <div className="flex items-center gap-1 p-2 bg-gray-800/50 rounded-lg min-h-[96px]">
      <SortableContext
        items={cardOrder}
        strategy={horizontalListSortingStrategy}
      >
        {cardOrder.map((cardId) => {
          const card = cards[cardId];
          if (!card) return null;
          return (
            <SortableCard
              key={cardId}
              card={card}
              zoneId={zone.zone_id}
              selected={selectedCards.has(cardId)}
              onClick={() => onCardSelect?.(cardId)}
            />
          );
        })}
      </SortableContext>
      {cardOrder.length === 0 && (
        <span className="text-gray-500 text-sm px-4">Empty hand</span>
      )}
    </div>
  );
}
