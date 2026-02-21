import { useState } from "react";
import { DeckRecipe } from "../../types/enums";
import { createTable } from "../../api/tables";

interface Props {
  onClose: () => void;
  onCreated: (tableId: string) => void;
}

export function CreateTableModal({ onClose, onCreated }: Props) {
  const [displayName, setDisplayName] = useState("");
  const [deckRecipe, setDeckRecipe] = useState<DeckRecipe>(
    DeckRecipe.STANDARD_52,
  );
  const [maxSeats, setMaxSeats] = useState(4);
  const [researchMode, setResearchMode] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!displayName.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const table = await createTable({
        display_name: displayName.trim(),
        deck_recipe: deckRecipe,
        max_seats: maxSeats,
        research_mode: researchMode,
      });
      onCreated(table.table_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create table");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="bg-gray-800 rounded-lg p-6 w-full max-w-md shadow-xl">
        <h2 className="text-xl font-bold mb-4">Create Table</h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm text-gray-300 mb-1">
              Table Name
            </label>
            <input
              type="text"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded text-white focus:outline-none focus:border-blue-500"
              placeholder="Friday Night Euchre"
              autoFocus
              maxLength={64}
            />
          </div>

          <div>
            <label className="block text-sm text-gray-300 mb-1">Deck</label>
            <select
              value={deckRecipe}
              onChange={(e) => setDeckRecipe(e.target.value as DeckRecipe)}
              className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded text-white focus:outline-none focus:border-blue-500"
            >
              <option value={DeckRecipe.STANDARD_52}>Standard 52</option>
              <option value={DeckRecipe.EUCHRE_24}>Euchre 24</option>
              <option value={DeckRecipe.DOUBLE_PINOCHLE_80}>
                Double Pinochle 80
              </option>
            </select>
          </div>

          <div>
            <label className="block text-sm text-gray-300 mb-1">
              Max Seats
            </label>
            <input
              type="number"
              min={2}
              max={8}
              value={maxSeats}
              onChange={(e) => setMaxSeats(Number(e.target.value))}
              className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded text-white focus:outline-none focus:border-blue-500"
            />
          </div>

          <label className="flex items-center gap-2 text-sm text-gray-300">
            <input
              type="checkbox"
              checked={researchMode}
              onChange={(e) => setResearchMode(e.target.checked)}
              className="rounded bg-gray-700 border-gray-600"
            />
            Research mode
          </label>

          {error && <p className="text-red-400 text-sm">{error}</p>}

          <div className="flex gap-3 justify-end pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-gray-400 hover:text-white"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading || !displayName.trim()}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 rounded font-medium"
            >
              {loading ? "Creating..." : "Create"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
