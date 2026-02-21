import { apiFetch } from "../../api/client";
import type { DisputeReason } from "../../types/enums";

interface Props {
  disputeActionId: string | null;
  mySeatId: string | null;
  tableId: string;
  sendDispute: (
    actionId: string,
    reason?: DisputeReason,
    reasonText?: string,
  ) => void;
}

export function DisputeBanner({
  disputeActionId,
  tableId,
}: Props) {
  async function handleResolve(resolution: string) {
    try {
      await apiFetch(`/api/tables/${tableId}/dispute/resolve`, {
        method: "POST",
        body: JSON.stringify({ resolution }),
      });
    } catch (err) {
      console.error("Failed to resolve dispute:", err);
    }
  }

  return (
    <div className="bg-red-900/80 border-b border-red-700 px-4 py-2 flex items-center gap-4">
      <span className="text-red-200 font-bold text-sm">
        DISPUTE ACTIVE — play paused
      </span>
      {disputeActionId && (
        <span className="text-red-300 text-xs">
          Action: {disputeActionId.slice(-8)}
        </span>
      )}
      <div className="ml-auto flex gap-2">
        <button
          onClick={() => handleResolve("revised")}
          className="px-3 py-1 bg-yellow-600 hover:bg-yellow-500 rounded text-xs font-medium"
        >
          Revise
        </button>
        <button
          onClick={() => handleResolve("cancelled")}
          className="px-3 py-1 bg-red-600 hover:bg-red-500 rounded text-xs font-medium"
        >
          Cancel
        </button>
      </div>
    </div>
  );
}
