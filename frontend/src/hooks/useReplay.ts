import { useState, useCallback, useRef, useEffect } from "react";
import type { Event, TableState } from "../types/models";
import { EventType } from "../types/enums";
import { getEvents } from "../api/history";
import { tableReducer, initialTableState, type TableContextState } from "../state/reducers";

interface UseReplayReturn {
  loading: boolean;
  error: string | null;
  events: Event[];
  currentSeq: number;
  totalEvents: number;
  currentEvent: Event | null;
  state: TableContextState;
  isPlaying: boolean;
  speed: number;
  play: () => void;
  pause: () => void;
  step: (delta: number) => void;
  seek: (position: number) => void;
  setSpeed: (speed: number) => void;
}

export function useReplay(tableId: string): UseReplayReturn {
  const [events, setEvents] = useState<Event[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [currentSeq, setCurrentSeq] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [speed, setSpeed] = useState(1);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Load events on mount
  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    getEvents(tableId)
      .then((evts) => {
        if (!cancelled) {
          setEvents(evts);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err.message ?? "Failed to load events");
          setLoading(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [tableId]);

  // Rebuild state by replaying events 0..currentSeq
  const state = (() => {
    let s = initialTableState;
    for (let i = 0; i < currentSeq && i < events.length; i++) {
      const evt = events[i];
      // state_sync for TABLE_CREATED provides initial state
      if (evt.event_type === EventType.TABLE_CREATED && evt.data.table) {
        s = tableReducer(s, {
          type: "STATE_SYNC",
          state: evt.data.table as unknown as TableState,
          mySeatId: null,
        });
      } else {
        s = tableReducer(s, { type: "EVENT", event: evt });
      }
    }
    return s;
  })();

  const currentEvent = currentSeq > 0 && currentSeq <= events.length
    ? events[currentSeq - 1]
    : null;

  const step = useCallback(
    (delta: number) => {
      setCurrentSeq((prev) => Math.max(0, Math.min(prev + delta, events.length)));
    },
    [events.length],
  );

  const seek = useCallback(
    (position: number) => {
      setCurrentSeq(Math.max(0, Math.min(position, events.length)));
    },
    [events.length],
  );

  const pause = useCallback(() => {
    setIsPlaying(false);
  }, []);

  const play = useCallback(() => {
    setIsPlaying(true);
  }, []);

  // Playback timer
  useEffect(() => {
    if (isPlaying && events.length > 0) {
      const interval = Math.max(50, 500 / speed);
      timerRef.current = setInterval(() => {
        setCurrentSeq((prev) => {
          if (prev >= events.length) {
            setIsPlaying(false);
            return prev;
          }
          return prev + 1;
        });
      }, interval);
    }
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [isPlaying, speed, events.length]);

  return {
    loading,
    error,
    events,
    currentSeq,
    totalEvents: events.length,
    currentEvent,
    state,
    isPlaying,
    speed,
    play,
    pause,
    step,
    seek,
    setSpeed,
  };
}
