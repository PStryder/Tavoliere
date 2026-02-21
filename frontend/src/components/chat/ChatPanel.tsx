import { useState, useRef, useEffect } from "react";
import type { ChatMessage as ChatMsg, Seat } from "../../types/models";
import { ChatMessage } from "./ChatMessage";

interface Props {
  messages: ChatMsg[];
  seats: Seat[];
  onSend: (text: string) => void;
}

export function ChatPanel({ messages, seats, onSend }: Props) {
  const [text, setText] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages.length]);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!text.trim()) return;
    onSend(text.trim());
    setText("");
  }

  const seatMap = new Map(seats.map((s) => [s.seat_id, s]));

  return (
    <div className="w-72 border-l border-gray-700 flex flex-col bg-gray-800/50">
      <div className="px-3 py-2 border-b border-gray-700 text-sm font-medium text-gray-400">
        Chat
      </div>
      <div ref={scrollRef} className="flex-1 overflow-y-auto py-1">
        {messages.length === 0 && (
          <p className="text-gray-600 text-xs text-center py-4">
            No messages yet
          </p>
        )}
        {messages.map((m) => (
          <ChatMessage
            key={m.message_id}
            message={m}
            seat={seatMap.get(m.seat_id)}
          />
        ))}
      </div>
      <form
        onSubmit={handleSubmit}
        className="border-t border-gray-700 p-2 flex gap-2"
      >
        <input
          type="text"
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="Type a message..."
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
    </div>
  );
}
