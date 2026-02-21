import { useCallback, useRef } from "react";
import type { Event } from "../../types/models";
import { EventType } from "../../types/enums";

interface Props {
  events: Event[];
  currentSeq: number;
  onSeek: (position: number) => void;
}

function eventColor(type: EventType): string {
  switch (type) {
    case EventType.ACTION_COMMITTED:
    case EventType.ACTION_FINALIZED:
      return "bg-green-500";
    case EventType.DISPUTE_OPENED:
    case EventType.DISPUTE_RESOLVED:
      return "bg-red-500";
    case EventType.ACTION_ROLLED_BACK:
      return "bg-yellow-500";
    case EventType.CHAT_MESSAGE:
      return "bg-blue-500";
    default:
      return "bg-gray-600";
  }
}

export function ReplayTimeline({ events, currentSeq, onSeek }: Props) {
  const barRef = useRef<HTMLDivElement>(null);

  const handleClick = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      if (!barRef.current || events.length === 0) return;
      const rect = barRef.current.getBoundingClientRect();
      const ratio = (e.clientX - rect.left) / rect.width;
      onSeek(Math.round(ratio * events.length));
    },
    [events.length, onSeek],
  );

  const progress = events.length > 0 ? (currentSeq / events.length) * 100 : 0;

  return (
    <div className="px-4 py-2 bg-gray-800">
      <div
        ref={barRef}
        className="relative h-6 bg-gray-700 rounded cursor-pointer overflow-hidden"
        onClick={handleClick}
      >
        {/* Progress fill */}
        <div
          className="absolute inset-y-0 left-0 bg-blue-600/30"
          style={{ width: `${progress}%` }}
        />

        {/* Event markers */}
        {events.map((evt, i) => {
          const left = ((i + 1) / events.length) * 100;
          const color = eventColor(evt.event_type);
          return (
            <div
              key={i}
              className={`absolute top-1 w-0.5 h-4 ${color} opacity-60`}
              style={{ left: `${left}%` }}
            />
          );
        })}

        {/* Scrub handle */}
        <div
          className="absolute top-0 w-1 h-full bg-white rounded"
          style={{ left: `${progress}%`, transform: "translateX(-50%)" }}
        />
      </div>
      <div className="flex justify-between mt-1 text-[10px] text-gray-500">
        <span>Start</span>
        <span>
          Green=commits, Red=disputes, Yellow=rollbacks, Blue=chat
        </span>
        <span>End</span>
      </div>
    </div>
  );
}
