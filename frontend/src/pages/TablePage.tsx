import { useEffect, useState, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import { useTable } from "../hooks/useTable";
import { TableProvider } from "../state/TableContext";
import { useTableSocket } from "../ws/useTableSocket";
import { getTable, leaveTable } from "../api/tables";
import { TableSurface } from "../components/table/TableSurface";
import { PendingActionBar } from "../components/table/PendingActionBar";
import { DisputeBanner } from "../components/table/DisputeBanner";
import { PhaseLabel } from "../components/table/PhaseLabel";
import { AckPosturePanel } from "../components/table/AckPosturePanel";
import { ChatPanel } from "../components/chat/ChatPanel";
import { ConsentModal } from "../components/consent/ConsentModal";

function TablePageInner() {
  const { tableId } = useParams<{ tableId: string }>();
  const navigate = useNavigate();
  const { token, identity, isAuthenticated } = useAuth();
  const { state, dispatch } = useTable();
  const [showConsent, setShowConsent] = useState(false);

  const handleResync = useCallback(async () => {
    if (!tableId) return;
    try {
      const fresh = await getTable(tableId);
      const mySeat = fresh.seats.find(
        (s) => s.identity_id === identity?.identity_id,
      );
      dispatch({
        type: "STATE_SYNC",
        state: fresh,
        mySeatId: mySeat?.seat_id ?? null,
      });
    } catch {
      /* will retry on next event */
    }
  }, [tableId, identity, dispatch]);

  const {
    connected,
    lastError,
    sendAction,
    sendAck,
    sendNack,
    sendDispute,
    sendChat,
    sendAckPosture,
  } = useTableSocket({
    tableId: tableId ?? "",
    token: token ?? "",
    identityId: identity?.identity_id ?? "",
    dispatch,
    onNeedsResync: handleResync,
  });

  // Handle resync flag
  useEffect(() => {
    if (state.needsResync) {
      handleResync();
    }
  }, [state.needsResync, handleResync]);

  // Redirect if not auth'd
  useEffect(() => {
    if (!isAuthenticated) navigate("/");
  }, [isAuthenticated, navigate]);

  // Check if research mode needs consent
  useEffect(() => {
    if (state.table?.research_mode && !showConsent) {
      // Show consent modal on first load for research tables
      setShowConsent(true);
    }
  }, [state.table?.research_mode]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleLeave = useCallback(async () => {
    if (!tableId) return;
    try {
      await leaveTable(tableId);
    } catch {
      /* best-effort */
    }
    navigate("/lobby");
  }, [tableId, navigate]);

  if (!tableId) return null;

  return (
    <div className="h-screen flex flex-col bg-gray-900">
      {/* Top bar */}
      <div className="flex items-center justify-between px-4 py-2 bg-gray-800 border-b border-gray-700">
        <div className="flex items-center gap-4">
          <button
            onClick={handleLeave}
            className="text-sm text-gray-400 hover:text-white"
          >
            &larr; Lobby
          </button>
          <span className="font-bold">
            {state.table?.display_name ?? "Loading..."}
          </span>
          {state.table && <PhaseLabel phase={state.table.phase} sendAction={sendAction} />}
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

      {/* Dispute banner */}
      {state.table?.dispute_active && (
        <DisputeBanner
          disputeActionId={state.table.dispute_action_id}
          mySeatId={state.mySeatId}
          sendDispute={sendDispute}
          tableId={tableId}
        />
      )}

      {/* Main content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Game area */}
        <div className="flex-1 flex flex-col">
          <div className="flex-1 overflow-auto">
            <TableSurface sendAction={sendAction} />
          </div>

          {/* Pending actions */}
          {state.pendingActions.length > 0 && (
            <PendingActionBar
              pendingActions={state.pendingActions}
              mySeatId={state.mySeatId}
              seats={state.table?.seats ?? []}
              onAck={sendAck}
              onNack={sendNack}
            />
          )}

          {/* ACK posture */}
          {state.table && state.mySeatId && (
            <AckPosturePanel
              seats={state.table.seats}
              mySeatId={state.mySeatId}
              onUpdate={sendAckPosture}
            />
          )}
        </div>

        {/* Chat panel */}
        <ChatPanel
          messages={state.chatMessages}
          seats={state.table?.seats ?? []}
          onSend={sendChat}
        />
      </div>

      {/* Consent modal */}
      {showConsent && state.table?.research_mode && (
        <ConsentModal
          tableId={tableId}
          onAccept={() => setShowConsent(false)}
          onDecline={() => navigate("/lobby")}
        />
      )}
    </div>
  );
}

export function TablePage() {
  return (
    <TableProvider>
      <TablePageInner />
    </TableProvider>
  );
}
