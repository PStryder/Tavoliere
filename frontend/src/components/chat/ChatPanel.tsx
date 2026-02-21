import { useState, useRef, useEffect } from "react";
import type { ChatMessage as ChatMsg, Seat } from "../../types/models";
import { ChatMessage } from "./ChatMessage";

interface Props {
  messages: ChatMsg[];
  seats: Seat[];
  onSend: (text: string, channel?: string) => void;
  spectating?: boolean;
}

export function ChatPanel({ messages, seats, onSend, spectating }: Props) {
  const [text, setText] = useState("");
  const [activeChannel, setActiveChannel] = useState<"game" | "spectator">(
    spectating ? "spectator" : "game",
  );
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages.length]);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!text.trim()) return;
    if (spectating) {
      onSend(text.trim(), "spectator");
    } else {
      onSend(text.trim());
    }
    setText("");
  }

  const seatMap = new Map(seats.map((s) => [s.seat_id, s]));

  // Filter messages by channel when spectating
  const filtered = spectating
    ? messages.filter((m) => (m.channel ?? "game") === activeChannel)
    : messages;

  const isReadOnly = spectating && activeChannel === "game";

  return (
    <div className="w-72 border-l border-gray-700 flex flex-col bg-gray-800/50">
      {spectating ? (
        <div className="flex border-b border-gray-700">
          <button
            onClick={() => setActiveChannel("game")}
            className={`flex-1 px-3 py-2 text-xs font-medium ${
              activeChannel === "game"
                ? "text-white border-b-2 border-blue-500"
                : "text-gray-500 hover:text-gray-300"
            }`}
          >
            Game Chat
          </button>
          <button
            onClick={() => setActiveChannel("spectator")}
            className={`flex-1 px-3 py-2 text-xs font-medium ${
              activeChannel === "spectator"
                ? "text-white border-b-2 border-green-500"
                : "text-gray-500 hover:text-gray-300"
            }`}
          >
            Spectator Chat
          </button>
        </div>
      ) : (
        <div className="px-3 py-2 border-b border-gray-700 text-sm font-medium text-gray-400">
          Chat
        </div>
      )}
      <div ref={scrollRef} className="flex-1 overflow-y-auto py-1">
        {filtered.length === 0 && (
          <p className="text-gray-600 text-xs text-center py-4">
            No messages yet
          </p>
        )}
        {filtered.map((m) => (
          <ChatMessage
            key={m.message_id}
            message={m}
            seat={seatMap.get(m.seat_id)}
          />
        ))}
      </div>
      {!isReadOnly && (
        <form
          onSubmit={handleSubmit}
          className="border-t border-gray-700 p-2 flex gap-2"
        >
          <input
            type="text"
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder={
              spectating ? "Spectator chat..." : "Type a message..."
            }
            className="flex-1 text-sm bg-gray-700 border border-gray-600 rounded px-2 py-1 text-white focus:outline-none focus:border-blue-500"
            maxLength={500}
          />
          <button
            type="submit"
            disabled={!text.trim()}
            className="px-3 py-1 bg-blue-600 hover:bg-blue-500 disabled:opacity-40 rounded text-sm font-medium"
          >
            Send
          </button>
        </form>
      )}
      {isReadOnly && (
        <div className="border-t border-gray-700 p-2 text-xs text-gray-500 text-center">
          Game chat is read-only for spectators
        </div>
      )}
    </div>
  );
}
