import { useState, useEffect } from "react";
import { ConsentTier } from "../../types/enums";
import {
  getConsentRequirements,
  submitConsent,
  type ConsentRequirements,
} from "../../api/consent";

interface Props {
  tableId: string;
  onAccept: () => void;
  onDecline: () => void;
}

const TIER_LABELS: Record<string, string> = {
  [ConsentTier.RESEARCH_LOGGING]: "Research logging",
  [ConsentTier.CHAT_STORAGE]: "Chat message storage",
  [ConsentTier.TRAINING_USE]: "Use for AI training",
  [ConsentTier.PUBLICATION]: "Publication of aggregate data",
  [ConsentTier.PUBLICATION_EXCERPTS]: "Publication of gameplay excerpts",
  [ConsentTier.LONGITUDINAL_LINKING]: "Link sessions longitudinally",
  [ConsentTier.AI_DISCLOSURE_ACK]: "Acknowledge AI player disclosure",
};

export function ConsentModal({ tableId, onAccept, onDecline }: Props) {
  const [requirements, setRequirements] = useState<ConsentRequirements | null>(
    null,
  );
  const [tiers, setTiers] = useState<Record<string, boolean>>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getConsentRequirements(tableId)
      .then((reqs) => {
        setRequirements(reqs);
        // Pre-check required tiers
        const initial: Record<string, boolean> = {};
        for (const t of reqs.required) initial[t] = true;
        for (const t of reqs.optional) initial[t] = false;
        setTiers(initial);
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : "Failed to load consent requirements");
      });
  }, [tableId]);

  async function handleAccept() {
    setLoading(true);
    setError(null);
    try {
      await submitConsent(tableId, tiers);
      onAccept();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to submit consent");
    } finally {
      setLoading(false);
    }
  }

  if (!requirements) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
        <div className="bg-gray-800 rounded-lg p-6 w-full max-w-md">
          <p className="text-gray-400">Loading consent requirements...</p>
        </div>
      </div>
    );
  }

  const allRequiredChecked = requirements.required.every((t) => tiers[t]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="bg-gray-800 rounded-lg p-6 w-full max-w-md shadow-xl max-h-[80vh] overflow-y-auto">
        <h2 className="text-xl font-bold mb-2">Research Consent</h2>
        <p className="text-gray-400 text-sm mb-4">
          This table has research mode enabled. Please review and consent to the
          following data collection practices.
        </p>

        {requirements.required.length > 0 && (
          <div className="mb-4">
            <h3 className="text-sm font-medium text-gray-300 mb-2">
              Required
            </h3>
            {requirements.required.map((t) => (
              <label
                key={t}
                className="flex items-center gap-2 text-sm text-gray-300 py-1"
              >
                <input
                  type="checkbox"
                  checked={tiers[t] ?? false}
                  onChange={(e) =>
                    setTiers((prev) => ({ ...prev, [t]: e.target.checked }))
                  }
                  className="rounded bg-gray-700 border-gray-600"
                />
                {TIER_LABELS[t] ?? t}
              </label>
            ))}
          </div>
        )}

        {requirements.optional.length > 0 && (
          <div className="mb-4">
            <h3 className="text-sm font-medium text-gray-300 mb-2">
              Optional
            </h3>
            {requirements.optional.map((t) => (
              <label
                key={t}
                className="flex items-center gap-2 text-sm text-gray-300 py-1"
              >
                <input
                  type="checkbox"
                  checked={tiers[t] ?? false}
                  onChange={(e) =>
                    setTiers((prev) => ({ ...prev, [t]: e.target.checked }))
                  }
                  className="rounded bg-gray-700 border-gray-600"
                />
                {TIER_LABELS[t] ?? t}
              </label>
            ))}
          </div>
        )}

        {error && <p className="text-red-400 text-sm mb-3">{error}</p>}

        <div className="flex gap-3 justify-end">
          <button
            onClick={onDecline}
            className="px-4 py-2 text-gray-400 hover:text-white"
          >
            Decline
          </button>
          <button
            onClick={handleAccept}
            disabled={loading || !allRequiredChecked}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 rounded font-medium"
          >
            {loading ? "Submitting..." : "Accept"}
          </button>
        </div>
      </div>
    </div>
  );
}
