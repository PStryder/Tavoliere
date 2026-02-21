import { useState, useEffect } from "react";
import {
  DndContext,
  closestCenter,
  type DragEndEvent,
} from "@dnd-kit/core";
import {
  SortableContext,
  horizontalListSortingStrategy,
  useSortable,
  arrayMove,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import type { Card, Zone } from "../../types/models";
import { Suit } from "../../types/enums";

interface Props {
  zone: Zone;
  cards: Record<string, Card>;
  onReorder: (newOrder: string[]) => void;
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

function SortableCard({
  card,
  selected,
  onClick,
}: {
  card: Card;
  selected: boolean;
  onClick: () => void;
}) {
  const { attributes, listeners, setNodeRef, transform, transition } =
    useSortable({ id: card.unique_id });

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
  onReorder,
  onCardSelect,
  selectedCards = new Set(),
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

  function handleDragEnd(event: DragEndEvent) {
    const { active, over } = event;
    if (!over || active.id === over.id) return;

    const oldIndex = cardOrder.indexOf(active.id as string);
    const newIndex = cardOrder.indexOf(over.id as string);
    const newOrder = arrayMove(cardOrder, oldIndex, newIndex);
    setCardOrder(newOrder);
    onReorder(newOrder);
  }

  return (
    <div className="flex items-center gap-1 p-2 bg-gray-800/50 rounded-lg min-h-[96px]">
      <DndContext collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
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
                selected={selectedCards.has(cardId)}
                onClick={() => onCardSelect?.(cardId)}
              />
            );
          })}
        </SortableContext>
      </DndContext>
      {cardOrder.length === 0 && (
        <span className="text-gray-500 text-sm px-4">Empty hand</span>
      )}
    </div>
  );
}
