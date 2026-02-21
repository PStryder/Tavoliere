import { useState } from "react";
import { ActionType } from "../../types/enums";
import type { ActionIntent } from "../../types/models";

interface Props {
  phase: string;
  sendAction: (intent: ActionIntent) => void;
}

export function PhaseLabel({ phase, sendAction }: Props) {
  const [editing, setEditing] = useState(false);
  const [value, setValue] = useState(phase);

  function handleSubmit() {
    if (value.trim() && value.trim() !== phase) {
      sendAction({
        action_type: ActionType.SET_PHASE,
        phase_label: value.trim(),
      });
    }
    setEditing(false);
  }

  if (editing) {
    return (
      <input
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onBlur={handleSubmit}
        onKeyDown={(e) => {
          if (e.key === "Enter") handleSubmit();
          if (e.key === "Escape") setEditing(false);
        }}
        className="text-sm bg-gray-700 border border-gray-600 rounded px-2 py-0.5 text-white w-32"
        autoFocus
      />
    );
  }

  return (
    <button
      onClick={() => {
        setValue(phase);
        setEditing(true);
      }}
      className="text-sm text-gray-400 hover:text-white bg-gray-700/50 px-2 py-0.5 rounded"
      title="Click to change phase"
    >
      Phase: {phase || "—"}
    </button>
  );
}
