import { useEffect, useRef } from "react";
import { ActionType } from "../../types/enums";
import type { ActionIntent } from "../../types/models";

interface Props {
  x: number;
  y: number;
  zoneId?: string;
  cardIds?: string[];
  onAction: (intent: ActionIntent) => void;
  onClose: () => void;
}

export function ActionMenu({
  x,
  y,
  zoneId,
  cardIds,
  onAction,
  onClose,
}: Props) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        onClose();
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [onClose]);

  const actions = [
    {
      label: "Shuffle",
      type: ActionType.SHUFFLE,
      show: !!zoneId,
    },
    {
      label: "Reveal",
      type: ActionType.SELF_REVEAL,
      show: cardIds && cardIds.length > 0,
    },
    {
      label: "Deal",
      type: ActionType.DEAL_ROUND_ROBIN,
      show: !!zoneId,
    },
  ].filter((a) => a.show);

  if (actions.length === 0) return null;

  return (
    <div
      ref={ref}
      className="fixed z-50 bg-gray-800 border border-gray-600 rounded shadow-xl py-1 min-w-[140px]"
      style={{ left: x, top: y }}
    >
      {actions.map((a) => (
        <button
          key={a.type}
          onClick={() => {
            onAction({
              action_type: a.type,
              card_ids: cardIds,
              source_zone_id: zoneId,
            });
            onClose();
          }}
          className="w-full text-left px-3 py-1.5 text-sm hover:bg-gray-700 text-gray-300 hover:text-white"
        >
          {a.label}
        </button>
      ))}
    </div>
  );
}
