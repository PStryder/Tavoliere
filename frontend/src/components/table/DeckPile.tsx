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
      className="w-14 h-20 rounded-md bg-blue-900 border-2 border-blue-700 flex flex-col items-center justify-center hover:border-blue-500 transition-colors"
      title={`${zone.label || "Deck"} (${count} cards)`}
    >
      <div className="w-8 h-12 border border-blue-600 rounded-sm opacity-40" />
      <span className="text-xs text-blue-300 mt-0.5 font-medium">{count}</span>
    </button>
  );
}
