import { useState, useCallback } from "react";
import { DndContext, type DragEndEvent } from "@dnd-kit/core";
import { useTable } from "../../hooks/useTable";
import { ZoneKind, ZoneVisibility, ActionType } from "../../types/enums";
import type { Zone, ActionIntent } from "../../types/models";
import { HandZone } from "./HandZone";
import { PublicZone } from "./PublicZone";
import { SeatOwnedZone } from "./SeatOwnedZone";
import { SeatDisplay } from "./SeatDisplay";
import { ActionMenu } from "./ActionMenu";

interface Props {
  sendAction: (intent: ActionIntent) => void;
}

interface ContextMenuState {
  x: number;
  y: number;
  zoneId?: string;
  cardIds?: string[];
}

export function TableSurface({ sendAction }: Props) {
  const { state } = useTable();
  const { table, mySeatId } = state;
  const [selectedCards, setSelectedCards] = useState<Set<string>>(new Set());
  const [contextMenu, setContextMenu] = useState<ContextMenuState | null>(null);

  if (!table) return null;

  const { seats, zones, cards } = table;

  // Find my seat index and arrange other seats relative to me
  const myIdx = seats.findIndex((s) => s.seat_id === mySeatId);
  const orderedSeats =
    myIdx >= 0
      ? [...seats.slice(myIdx), ...seats.slice(0, myIdx)]
      : seats;

  // Me = bottom, partner = top, left/right opponents
  const me = orderedSeats[0];
  const partner = orderedSeats.length >= 3 ? orderedSeats[2] : undefined;
  const leftOpp = orderedSeats.length >= 2 ? orderedSeats[1] : undefined;
  const rightOpp = orderedSeats.length >= 4 ? orderedSeats[3] : undefined;

  // Zone helpers
  const myHand = zones.find(
    (z) =>
      z.kind === ZoneKind.HAND &&
      z.owner_seat_id === mySeatId,
  );

  const publicZones = zones.filter(
    (z) =>
      z.visibility === ZoneVisibility.PUBLIC &&
      z.kind !== ZoneKind.HAND,
  );

  const seatOwnedZones = (seatId: string) =>
    zones.filter(
      (z) =>
        z.owner_seat_id === seatId &&
        z.kind !== ZoneKind.HAND &&
        z.visibility !== ZoneVisibility.PRIVATE,
    );

  const handleCardSelect = useCallback((cardId: string) => {
    setSelectedCards((prev) => {
      const next = new Set(prev);
      if (next.has(cardId)) next.delete(cardId);
      else next.add(cardId);
      return next;
    });
  }, []);

  const handleReorder = useCallback(
    (newOrder: string[]) => {
      sendAction({
        action_type: ActionType.REORDER,
        new_order: newOrder,
        source_zone_id: myHand?.zone_id,
      });
    },
    [sendAction, myHand],
  );

  const handleDrop = useCallback(
    (event: DragEndEvent) => {
      const { active, over } = event;
      if (!over || !myHand) return;

      const targetZone = over.data.current?.zone as Zone | undefined;
      if (!targetZone) return;

      const cardIds = selectedCards.size > 0
        ? Array.from(selectedCards)
        : [active.id as string];

      sendAction({
        action_type:
          cardIds.length > 1
            ? ActionType.MOVE_CARDS_BATCH
            : ActionType.MOVE_CARD,
        card_ids: cardIds,
        source_zone_id: myHand.zone_id,
        target_zone_id: targetZone.zone_id,
      });
      setSelectedCards(new Set());
    },
    [sendAction, myHand, selectedCards],
  );

  const handleDeckClick = useCallback(
    (deckZone: Zone) => {
      if (!myHand) return;
      // Draw top card from deck to hand
      sendAction({
        action_type: ActionType.MOVE_CARD,
        card_ids: deckZone.card_ids.length > 0 ? [deckZone.card_ids[0]] : [],
        source_zone_id: deckZone.zone_id,
        target_zone_id: myHand.zone_id,
      });
    },
    [sendAction, myHand],
  );

  const handleContextMenu = useCallback(
    (e: React.MouseEvent, zoneId?: string, cardIds?: string[]) => {
      e.preventDefault();
      setContextMenu({
        x: e.clientX,
        y: e.clientY,
        zoneId,
        cardIds: cardIds ?? (selectedCards.size > 0 ? Array.from(selectedCards) : undefined),
      });
    },
    [selectedCards],
  );

  return (
    <DndContext onDragEnd={handleDrop}>
      <div
        className="grid grid-rows-[auto_1fr_auto] grid-cols-[auto_1fr_auto] gap-4 h-full p-4"
        onContextMenu={(e) => handleContextMenu(e)}
      >
        {/* Top: Partner */}
        <div className="col-span-3 flex flex-col items-center gap-2">
          {partner && (
            <>
              <SeatDisplay
                seat={partner}
                isHost={partner.seat_id === table.host_seat_id}
              />
              <div className="flex gap-1">
                {seatOwnedZones(partner.seat_id).map((z) => (
                  <SeatOwnedZone key={z.zone_id} zone={z} cards={cards} />
                ))}
              </div>
            </>
          )}
        </div>

        {/* Left: Opponent */}
        <div className="flex flex-col items-center justify-center gap-2">
          {leftOpp && (
            <>
              <SeatDisplay
                seat={leftOpp}
                isHost={leftOpp.seat_id === table.host_seat_id}
              />
              <div className="flex flex-col gap-1">
                {seatOwnedZones(leftOpp.seat_id).map((z) => (
                  <SeatOwnedZone key={z.zone_id} zone={z} cards={cards} />
                ))}
              </div>
            </>
          )}
        </div>

        {/* Center: Public zones */}
        <div className="flex flex-wrap gap-3 items-center justify-center">
          {publicZones.map((z) => (
            <div
              key={z.zone_id}
              onContextMenu={(e) => handleContextMenu(e, z.zone_id)}
            >
              <PublicZone
                zone={z}
                cards={cards}
                onDeckClick={
                  z.kind === ZoneKind.DECK ? () => handleDeckClick(z) : undefined
                }
              />
            </div>
          ))}
        </div>

        {/* Right: Opponent */}
        <div className="flex flex-col items-center justify-center gap-2">
          {rightOpp && (
            <>
              <SeatDisplay
                seat={rightOpp}
                isHost={rightOpp.seat_id === table.host_seat_id}
              />
              <div className="flex flex-col gap-1">
                {seatOwnedZones(rightOpp.seat_id).map((z) => (
                  <SeatOwnedZone key={z.zone_id} zone={z} cards={cards} />
                ))}
              </div>
            </>
          )}
        </div>

        {/* Bottom: Me */}
        <div className="col-span-3 flex flex-col items-center gap-2">
          {me && (
            <>
              <div className="flex gap-1 mb-1">
                {seatOwnedZones(me.seat_id).map((z) => (
                  <SeatOwnedZone key={z.zone_id} zone={z} cards={cards} />
                ))}
              </div>
              {myHand && (
                <div onContextMenu={(e) => handleContextMenu(e, myHand.zone_id)}>
                  <HandZone
                    zone={myHand}
                    cards={cards}
                    onReorder={handleReorder}
                    onCardSelect={handleCardSelect}
                    selectedCards={selectedCards}
                  />
                </div>
              )}
              <SeatDisplay
                seat={me}
                isMe
                isHost={me.seat_id === table.host_seat_id}
              />
            </>
          )}
        </div>
      </div>

      {/* Right-click context menu */}
      {contextMenu && (
        <ActionMenu
          x={contextMenu.x}
          y={contextMenu.y}
          zoneId={contextMenu.zoneId}
          cardIds={contextMenu.cardIds}
          onAction={(intent) => {
            sendAction(intent);
            setSelectedCards(new Set());
          }}
          onClose={() => setContextMenu(null)}
        />
      )}
    </DndContext>
  );
}
