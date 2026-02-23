import { useState } from "react";
import { ActionType, ZoneKind } from "../../types/enums";
import type { ActionIntent, Zone } from "../../types/models";
import { CreateZoneModal } from "./CreateZoneModal";
import { DealPopover } from "./DealPopover";

interface Props {
  sendAction: (intent: ActionIntent) => void;
  selectedCards: Set<string>;
  zones: Zone[];
  seatIds: string[];
}

export function ActionToolbar({
  sendAction,
  selectedCards,
  zones,
  seatIds,
}: Props) {
  const [showCreateZone, setShowCreateZone] = useState(false);
  const [showDeal, setShowDeal] = useState(false);

  const deckZone = zones.find((z) => z.kind === ZoneKind.DECK);

  const handleShuffle = () => {
    if (!deckZone) return;
    sendAction({
      action_type: ActionType.SHUFFLE,
      source_zone_id: deckZone.zone_id,
    });
  };

  const handleReveal = () => {
    if (selectedCards.size === 0) return;
    sendAction({
      action_type: ActionType.SELF_REVEAL,
      card_ids: Array.from(selectedCards),
    });
  };

  const handleUndo = () => {
    sendAction({ action_type: ActionType.UNDO });
  };

  return (
    <>
      <div className="flex items-center gap-2 px-4 py-1.5 bg-gray-800/80 border-b border-gray-700">
        {/* Shuffle */}
        <button
          onClick={handleShuffle}
          disabled={!deckZone}
          className="flex items-center gap-1.5 px-3 py-1 rounded text-sm bg-gray-700 hover:bg-gray-600 text-gray-300 hover:text-white disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          title="Shuffle the deck"
        >
          <span className="text-base">&#x2694;</span>
          Shuffle
        </button>

        {/* Deal */}
        <div className="relative">
          <button
            onClick={() => setShowDeal((v) => !v)}
            disabled={!deckZone || deckZone.card_ids.length === 0}
            className="flex items-center gap-1.5 px-3 py-1 rounded text-sm bg-gray-700 hover:bg-gray-600 text-gray-300 hover:text-white disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            title="Deal cards to players"
          >
            <span className="text-base">&#x2660;</span>
            Deal
          </button>
          {showDeal && deckZone && (
            <DealPopover
              deckZone={deckZone}
              zones={zones}
              seatIds={seatIds}
              sendAction={sendAction}
              onClose={() => setShowDeal(false)}
            />
          )}
        </div>

        {/* Reveal */}
        <button
          onClick={handleReveal}
          disabled={selectedCards.size === 0}
          className="flex items-center gap-1.5 px-3 py-1 rounded text-sm bg-gray-700 hover:bg-gray-600 text-gray-300 hover:text-white disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          title={
            selectedCards.size > 0
              ? `Reveal ${selectedCards.size} selected card(s)`
              : "Select cards first to reveal"
          }
        >
          <span className="text-base">&#x1F441;</span>
          Reveal{selectedCards.size > 0 ? ` (${selectedCards.size})` : ""}
        </button>

        {/* Undo */}
        <button
          onClick={handleUndo}
          className="flex items-center gap-1.5 px-3 py-1 rounded text-sm bg-gray-700 hover:bg-gray-600 text-gray-300 hover:text-white transition-colors"
          title="Undo last action"
        >
          <span className="text-base">&#x21A9;</span>
          Undo
        </button>

        <div className="w-px h-5 bg-gray-600 mx-1" />

        {/* New Zone */}
        <button
          onClick={() => setShowCreateZone(true)}
          className="flex items-center gap-1.5 px-3 py-1 rounded text-sm bg-gray-700 hover:bg-gray-600 text-gray-300 hover:text-white transition-colors"
          title="Create a new zone"
        >
          <span className="text-base">+</span>
          New Zone
        </button>
      </div>

      {showCreateZone && (
        <CreateZoneModal
          sendAction={sendAction}
          onClose={() => setShowCreateZone(false)}
        />
      )}
    </>
  );
}
