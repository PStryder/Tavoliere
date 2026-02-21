import { useState, useEffect } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import { useReplay } from "../hooks/useReplay";
import { ReplayControls } from "../components/replay/ReplayControls";
import { ReplayTimeline } from "../components/replay/ReplayTimeline";
import { SeatPerspectivePicker } from "../components/replay/SeatPerspectivePicker";
import { PublicZone } from "../components/table/PublicZone";
import { SeatDisplay } from "../components/table/SeatDisplay";
import { SeatOwnedZone } from "../components/table/SeatOwnedZone";
import { ZoneKind, ZoneVisibility } from "../types/enums";

export function ReplayPage() {
  const { tableId } = useParams<{ tableId: string }>();
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();
  const [perspective, setPerspective] = useState("__observer__");

  useEffect(() => {
    if (!isAuthenticated) navigate("/");
  }, [isAuthenticated, navigate]);

  const {
    loading,
    error,
    events,
    currentSeq,
    totalEvents,
    currentEvent,
    state,
    isPlaying,
    speed,
    play,
    pause,
    step,
    seek,
    setSpeed,
  } = useReplay(tableId ?? "");

  if (!tableId) return null;

  if (loading) {
    return (
      <div className="h-screen flex items-center justify-center bg-gray-900 text-gray-400">
        Loading replay...
      </div>
    );
  }

  if (error) {
    return (
      <div className="h-screen flex flex-col items-center justify-center bg-gray-900 gap-4">
        <p className="text-red-400">Failed to load replay: {error}</p>
        <Link to="/games" className="text-blue-400 hover:underline text-sm">
          Back to Game History
        </Link>
      </div>
    );
  }

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

  // Chat messages up to current position
  const chatMessages = state.chatMessages;

  return (
    <div className="h-screen flex flex-col bg-gray-900">
      {/* Top bar */}
      <div className="flex items-center justify-between px-4 py-2 bg-gray-800 border-b border-gray-700">
        <div className="flex items-center gap-4">
          <Link
            to="/games"
            className="text-sm text-gray-400 hover:text-white"
          >
            &larr; Game History
          </Link>
          <span className="font-bold">
            {table?.display_name ?? "Replay"}
          </span>
          <span className="text-xs bg-purple-600/30 text-purple-300 px-2 py-0.5 rounded">
            REPLAY
          </span>
        </div>
        {currentEvent && (
          <span className="text-xs text-gray-500">
            {currentEvent.event_type} @ {new Date(currentEvent.timestamp).toLocaleTimeString()}
          </span>
        )}
      </div>

      {/* Perspective picker */}
      {table && (
        <SeatPerspectivePicker
          seats={table.seats}
          activePerspective={perspective}
          onSelect={setPerspective}
        />
      )}

      {/* Game area */}
      <div className="flex-1 overflow-auto p-4">
        {table ? (
          <div className="space-y-6">
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
            <div className="flex flex-wrap gap-3 justify-center">
              {publicZones.map((z) => (
                <PublicZone key={z.zone_id} zone={z} cards={table.cards} />
              ))}
            </div>

            {/* Chat messages */}
            {chatMessages.length > 0 && (
              <div className="max-w-md mx-auto bg-gray-800/50 rounded p-2">
                <div className="text-xs text-gray-500 mb-1">Chat</div>
                {chatMessages.slice(-5).map((m) => (
                  <div key={m.message_id} className="text-xs text-gray-400">
                    <span className="text-blue-400">{m.seat_id}</span>: {m.text}
                  </div>
                ))}
              </div>
            )}
          </div>
        ) : (
          <div className="text-center text-gray-500 py-8">
            {totalEvents === 0
              ? "No events to replay"
              : "Press Play to start replay"}
          </div>
        )}
      </div>

      {/* Timeline */}
      <ReplayTimeline events={events} currentSeq={currentSeq} onSeek={seek} />

      {/* Controls */}
      <ReplayControls
        isPlaying={isPlaying}
        currentSeq={currentSeq}
        totalEvents={totalEvents}
        speed={speed}
        onPlay={play}
        onPause={pause}
        onStep={step}
        onSetSpeed={setSpeed}
      />
    </div>
  );
}
