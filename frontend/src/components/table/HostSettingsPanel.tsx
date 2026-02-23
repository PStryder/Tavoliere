import { useState, useEffect, useCallback } from "react";
import type { TableSettings } from "../../types/models";
import { updateSettings } from "../../api/tables";

interface Props {
  tableId: string;
  settings: TableSettings;
  onClose: () => void;
}

export function HostSettingsPanel({ tableId, settings, onClose }: Props) {
  const [local, setLocal] = useState<TableSettings>(settings);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLocal(settings);
  }, [settings]);

  const handleSave = useCallback(async () => {
    setSaving(true);
    setError(null);
    try {
      await updateSettings(tableId, {
        objection_window_s: local.objection_window_s,
        phase_locked: local.phase_locked,
        shuffle_is_optimistic: local.shuffle_is_optimistic,
        intent_rate_max_count: local.intent_rate_max_count,
        intent_rate_window_s: local.intent_rate_window_s,
      });
      onClose();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to save");
    } finally {
      setSaving(false);
    }
  }, [tableId, local, onClose]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="bg-gray-800 rounded-lg p-6 w-full max-w-sm">
        <h2 className="text-lg font-bold mb-4">Table Settings</h2>

        <div className="space-y-4">
          {/* Objection window */}
          <div>
            <label className="block text-sm text-gray-300 mb-1">
              Objection window: {local.objection_window_s}s
            </label>
            <input
              type="range"
              min={2}
              max={10}
              step={1}
              value={local.objection_window_s}
              onChange={(e) =>
                setLocal((s) => ({
                  ...s,
                  objection_window_s: parseInt(e.target.value),
                }))
              }
              className="w-full"
            />
          </div>

          {/* Phase locked */}
          <label className="flex items-center gap-2 text-sm text-gray-300 cursor-pointer">
            <input
              type="checkbox"
              checked={local.phase_locked}
              onChange={(e) =>
                setLocal((s) => ({ ...s, phase_locked: e.target.checked }))
              }
              className="rounded bg-gray-700 border-gray-600"
            />
            Phase locked
          </label>

          {/* Shuffle optimistic */}
          <label className="flex items-center gap-2 text-sm text-gray-300 cursor-pointer">
            <input
              type="checkbox"
              checked={local.shuffle_is_optimistic}
              onChange={(e) =>
                setLocal((s) => ({
                  ...s,
                  shuffle_is_optimistic: e.target.checked,
                }))
              }
              className="rounded bg-gray-700 border-gray-600"
            />
            Shuffle is optimistic
          </label>

          {/* Rate limit */}
          <div>
            <label className="block text-sm text-gray-300 mb-1">
              Rate limit: {local.intent_rate_max_count} actions /{" "}
              {local.intent_rate_window_s}s
            </label>
            <div className="flex gap-2">
              <input
                type="number"
                min={1}
                max={100}
                value={local.intent_rate_max_count}
                onChange={(e) =>
                  setLocal((s) => ({
                    ...s,
                    intent_rate_max_count: parseInt(e.target.value) || 1,
                  }))
                }
                className="w-20 bg-gray-700 border border-gray-600 rounded px-2 py-1 text-sm focus:border-blue-500 focus:outline-none"
              />
              <span className="text-sm text-gray-500 self-center">per</span>
              <input
                type="number"
                min={1}
                max={120}
                value={local.intent_rate_window_s}
                onChange={(e) =>
                  setLocal((s) => ({
                    ...s,
                    intent_rate_window_s: parseInt(e.target.value) || 1,
                  }))
                }
                className="w-20 bg-gray-700 border border-gray-600 rounded px-2 py-1 text-sm focus:border-blue-500 focus:outline-none"
              />
              <span className="text-sm text-gray-500 self-center">sec</span>
            </div>
          </div>

          {error && (
            <div className="text-red-400 text-sm">{error}</div>
          )}
        </div>

        <div className="flex gap-3 justify-end mt-6">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded text-sm text-gray-400 hover:text-white"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={saving}
            className="px-4 py-2 rounded text-sm bg-blue-600 hover:bg-blue-500 disabled:opacity-50"
          >
            {saving ? "Saving..." : "Save"}
          </button>
        </div>
      </div>
    </div>
  );
}
