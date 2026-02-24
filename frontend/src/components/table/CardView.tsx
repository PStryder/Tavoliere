import { useDraggable } from "@dnd-kit/core";
import type { Card } from "../../types/models";
import { Suit } from "../../types/enums";

interface Props {
  card: Card;
  faceUp: boolean;
  selected?: boolean;
  onClick?: () => void;
  draggable?: boolean;
  onReveal?: () => void;
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
  [Suit.CLUBS]: "text-gray-900",
  [Suit.SPADES]: "text-gray-900",
};

export function CardView({
  card,
  faceUp,
  selected = false,
  onClick,
  draggable = false,
  onReveal,
}: Props) {
  const { attributes, listeners, setNodeRef, transform, isDragging } =
    useDraggable({
      id: card.unique_id,
      disabled: !draggable,
      data: { card },
    });

  const style = transform
    ? {
        transform: `translate(${transform.x}px, ${transform.y}px)`,
        zIndex: isDragging ? 50 : undefined,
      }
    : undefined;

  if (!faceUp) {
    return (
      <div
        ref={setNodeRef}
        style={style}
        {...attributes}
        {...listeners}
        className={`w-14 h-20 rounded-md bg-blue-900 border-2 border-blue-700 flex items-center justify-center select-none group relative ${
          selected ? "ring-2 ring-blue-400" : ""
        } ${onReveal ? "cursor-pointer hover:border-blue-400" : "cursor-default"} ${
          draggable ? "cursor-grab active:cursor-grabbing" : ""
        }`}
        onClick={onClick ?? onReveal}
      >
        <div className="w-8 h-14 border border-blue-600 rounded-sm opacity-40" />
        {onReveal && (
          <span className="absolute inset-0 flex items-center justify-center text-[10px] text-blue-300 opacity-0 group-hover:opacity-100 transition-opacity font-medium">
            Flip
          </span>
        )}
        {draggable && (
          <span className="absolute top-0.5 right-0.5 text-[8px] text-blue-500 opacity-0 group-hover:opacity-60">
            &#x283F;
          </span>
        )}
      </div>
    );
  }

  const suitSymbol = SUIT_SYMBOLS[card.suit] ?? "?";
  const suitColor = SUIT_COLORS[card.suit] ?? "text-white";

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...attributes}
      {...listeners}
      className={`w-14 h-20 rounded-md bg-white border-2 flex flex-col items-center justify-center select-none relative group ${
        selected
          ? "border-blue-400 ring-2 ring-blue-400"
          : "border-gray-300"
      } ${draggable ? "cursor-grab active:cursor-grabbing" : "cursor-default"} ${
        isDragging ? "opacity-60" : ""
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
      {draggable && (
        <span className="absolute top-0.5 right-0.5 text-[8px] text-gray-400 opacity-0 group-hover:opacity-60">
          &#x283F;
        </span>
      )}
    </div>
  );
}
