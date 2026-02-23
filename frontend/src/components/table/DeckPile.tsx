import type { Zone } from "../../types/models";

interface Props {
  zone: Zone;
  onClick?: () => void;
}

export function DeckPile({ zone, onClick }: Props) {
  const count = zone.card_ids.length;

  return (
    <button
      onClick={onClick}
      className="w-16 h-24 rounded-md bg-blue-900 border-2 border-blue-700 flex flex-col items-center justify-center hover:border-blue-400 hover:bg-blue-800 transition-colors group relative"
      title={`${zone.label || "Deck"} — click to draw (${count} cards)`}
    >
      <div className="w-8 h-10 border border-blue-600 rounded-sm opacity-40" />
      <span className="text-[10px] text-blue-300 mt-1 font-medium opacity-0 group-hover:opacity-100 transition-opacity">
        Draw
      </span>
      <span className="absolute top-1 right-1.5 text-[10px] text-blue-400 font-bold bg-blue-950/80 rounded px-1">
        {count}
      </span>
      <span className="absolute bottom-1 text-[9px] text-blue-500 font-medium">
        {zone.label || "Deck"}
      </span>
    </button>
  );
}
