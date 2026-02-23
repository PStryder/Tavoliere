import { useState } from "react";
import { ActionType, ZoneKind, ZoneVisibility } from "../../types/enums";
import type { ActionIntent } from "../../types/models";

interface Props {
  sendAction: (intent: ActionIntent) => void;
  onClose: () => void;
}

const ZONE_KINDS: { value: ZoneKind; label: string }[] = [
  { value: ZoneKind.CUSTOM, label: "Custom" },
  { value: ZoneKind.MELD, label: "Meld" },
  { value: ZoneKind.TRICKS_WON, label: "Tricks Won" },
  { value: ZoneKind.TRICK_PLAY, label: "Trick Play" },
  { value: ZoneKind.DISCARD, label: "Discard" },
  { value: ZoneKind.CENTER, label: "Center" },
];

const ZONE_VISIBILITIES: { value: ZoneVisibility; label: string }[] = [
  { value: ZoneVisibility.PUBLIC, label: "Public" },
  { value: ZoneVisibility.PRIVATE, label: "Private" },
  { value: ZoneVisibility.SEAT_PUBLIC, label: "Seat Public" },
];

export function CreateZoneModal({ sendAction, onClose }: Props) {
  const [label, setLabel] = useState("");
  const [kind, setKind] = useState<ZoneKind>(ZoneKind.CUSTOM);
  const [visibility, setVisibility] = useState<ZoneVisibility>(
    ZoneVisibility.PUBLIC,
  );

  const handleSubmit = () => {
    if (!label.trim()) return;
    sendAction({
      action_type: ActionType.CREATE_ZONE,
      zone_label: label.trim(),
      zone_kind: kind,
      zone_visibility: visibility,
    });
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="bg-gray-800 rounded-lg p-6 w-full max-w-sm">
        <h2 className="text-lg font-bold mb-4">Create Zone</h2>

        <div className="space-y-4">
          <div>
            <label className="block text-sm text-gray-300 mb-1">Label</label>
            <input
              type="text"
              value={label}
              onChange={(e) => setLabel(e.target.value)}
              placeholder="e.g. Discard Pile"
              className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
              autoFocus
              onKeyDown={(e) => {
                if (e.key === "Enter") handleSubmit();
                if (e.key === "Escape") onClose();
              }}
            />
          </div>

          <div>
            <label className="block text-sm text-gray-300 mb-1">Kind</label>
            <select
              value={kind}
              onChange={(e) => setKind(e.target.value as ZoneKind)}
              className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
            >
              {ZONE_KINDS.map((k) => (
                <option key={k.value} value={k.value}>
                  {k.label}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm text-gray-300 mb-1">
              Visibility
            </label>
            <select
              value={visibility}
              onChange={(e) =>
                setVisibility(e.target.value as ZoneVisibility)
              }
              className="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
            >
              {ZONE_VISIBILITIES.map((v) => (
                <option key={v.value} value={v.value}>
                  {v.label}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="flex gap-3 justify-end mt-6">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded text-sm text-gray-400 hover:text-white"
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={!label.trim()}
            className="px-4 py-2 rounded text-sm bg-blue-600 hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Create
          </button>
        </div>
      </div>
    </div>
  );
}
