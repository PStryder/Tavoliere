import { useEffect, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import { useTable } from "../hooks/useTable";
import { TableProvider } from "../state/TableContext";
import { useTableSocket } from "../ws/useTableSocket";
import { getTable } from "../api/tables";
import { SpectatorOverlay } from "../components/spectator/SpectatorOverlay";
import { ChatPanel } from "../components/chat/ChatPanel";
import { PublicZone } from "../components/table/PublicZone";
import { SeatDisplay } from "../components/table/SeatDisplay";
import { SeatOwnedZone } from "../components/table/SeatOwnedZone";
import { ZoneKind, ZoneVisibility } from "../types/enums";

function SpectatorPageInner() {
  const { tableId } = useParams<{ tableId: string }>();
  const navigate = useNavigate();
  const { token, identity, isAuthenticated } = useAuth();
  const { state, dispatch } = useTable();

  const handleResync = useCallback(async () => {
    if (!tableId) return;
    try {
      const fresh = await getTable(tableId);
      dispatch({ type: "STATE_SYNC", state: fresh, mySeatId: null });
    } catch {
      /* retry on next event */
    }
  }, [tableId, dispatch]);

  const { connected, lastError, sendChat } = useTableSocket({
    tableId: tableId ?? "",
    token: token ?? "",
    identityId: identity?.identity_id ?? "",
    dispatch,
    onNeedsResync: handleResync,
    mode: "spectate",
  });

  useEffect(() => {
    if (state.needsResync) handleResync();
  }, [state.needsResync, handleResync]);

  useEffect(() => {
    if (!isAuthenticated) navigate("/");
  }, [isAuthenticated, navigate]);

  // Navigate to summary on table destruction
  useEffect(() => {
    if (state.tableDestroyed && tableId) {
      navigate(`/table/${tableId}/summary`);
    }
  }, [state.tableDestroyed, tableId, navigate]);

  if (!tableId) return null;

  const table = state.table;

  const publicZones = table
    ? table.zones.filter(
        (z) => z.visibility === ZoneVisibility.PUBLIC && z.kind !== ZoneKind.HAND,
      )
    : [];

  const seatOwnedZones = (seatId: string) =>
    table
      ? table.zones.filter(
          (z) =>
            z.owner_seat_id === seatId &&
            z.kind !== ZoneKind.HAND &&
            z.visibility !== ZoneVisibility.PRIVATE,
        )
      : [];

  return (
    <div className="h-screen flex flex-col bg-gray-900">
      {/* Top bar */}
      <div className="flex items-center justify-between px-4 py-2 bg-gray-800 border-b border-gray-700">
        <div className="flex items-center gap-4">
          <button
            onClick={() => navigate("/lobby")}
            className="text-sm text-gray-400 hover:text-white"
          >
            &larr; Lobby
          </button>
          <span className="font-bold">
            {table?.display_name ?? "Loading..."}
          </span>
        </div>
        <div className="flex items-center gap-3 text-sm">
          <span
            className={`w-2 h-2 rounded-full ${
              connected ? "bg-green-500" : "bg-red-500"
            }`}
          />
          <span className="text-gray-400">
            {connected ? "Connected" : "Disconnected"}
          </span>
          {lastError && (
            <span className="text-red-400 text-xs">{lastError}</span>
          )}
        </div>
      </div>

      {/* Spectator overlay */}
      {table && (
        <SpectatorOverlay seats={table.seats} zones={table.zones} />
      )}

      {/* Main content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Game area - observer view */}
        <div className="flex-1 overflow-auto p-4">
          {table && (
            <div className="space-y-6">
              {/* Seats and their zones */}
              <div className="grid grid-cols-2 gap-4">
                {table.seats.map((seat) => (
                  <div key={seat.seat_id} className="space-y-2">
                    <SeatDisplay
                      seat={seat}
                      isHost={seat.seat_id === table.host_seat_id}
                    />
                    <div className="flex gap-1 flex-wrap">
                      {seatOwnedZones(seat.seat_id).map((z) => (
                        <SeatOwnedZone
                          key={z.zone_id}
                          zone={z}
                          cards={table.cards}
                        />
                      ))}
                    </div>
                  </div>
                ))}
              </div>

              {/* Public zones */}
              <div className="flex flex-wrap gap-3 justify-center">
                {publicZones.map((z) => (
                  <PublicZone key={z.zone_id} zone={z} cards={table.cards} />
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Chat panel with spectator tabs */}
        <ChatPanel
          messages={state.chatMessages}
          seats={table?.seats ?? []}
          onSend={sendChat}
          spectating
        />
      </div>
    </div>
  );
}

export function SpectatorPage() {
  return (
    <TableProvider>
      <SpectatorPageInner />
    </TableProvider>
  );
}
