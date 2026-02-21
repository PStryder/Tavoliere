interface Props {
  isPlaying: boolean;
  currentSeq: number;
  totalEvents: number;
  speed: number;
  onPlay: () => void;
  onPause: () => void;
  onStep: (delta: number) => void;
  onSetSpeed: (speed: number) => void;
}

const SPEEDS = [0.5, 1, 2, 4];

export function ReplayControls({
  isPlaying,
  currentSeq,
  totalEvents,
  speed,
  onPlay,
  onPause,
  onStep,
  onSetSpeed,
}: Props) {
  return (
    <div className="flex items-center gap-3 px-4 py-2 bg-gray-800 border-t border-gray-700">
      <button
        onClick={() => onStep(-1)}
        disabled={currentSeq <= 0}
        className="px-2 py-1 text-sm bg-gray-700 hover:bg-gray-600 disabled:opacity-40 rounded"
      >
        Step Back
      </button>

      <button
        onClick={isPlaying ? onPause : onPlay}
        disabled={!isPlaying && currentSeq >= totalEvents}
        className="px-3 py-1 text-sm bg-blue-600 hover:bg-blue-500 disabled:opacity-40 rounded font-medium"
      >
        {isPlaying ? "Pause" : "Play"}
      </button>

      <button
        onClick={() => onStep(1)}
        disabled={currentSeq >= totalEvents}
        className="px-2 py-1 text-sm bg-gray-700 hover:bg-gray-600 disabled:opacity-40 rounded"
      >
        Step Fwd
      </button>

      <span className="text-sm text-gray-400 ml-2">
        Event {currentSeq} / {totalEvents}
      </span>

      <div className="ml-auto flex items-center gap-2">
        <span className="text-xs text-gray-500">Speed:</span>
        {SPEEDS.map((s) => (
          <button
            key={s}
            onClick={() => onSetSpeed(s)}
            className={`px-2 py-0.5 text-xs rounded ${
              speed === s
                ? "bg-blue-600 text-white"
                : "bg-gray-700 text-gray-400 hover:bg-gray-600"
            }`}
          >
            {s}x
          </button>
        ))}
      </div>
    </div>
  );
}
