import { useState } from "react";
import { useAuth } from "../../hooks/useAuth";

interface Props {
  onClose: () => void;
  onSuccess: () => void;
}

export function LoginModal({ onClose, onSuccess }: Props) {
  const { login } = useAuth();
  const [name, setName] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    setLoading(true);
    setError(null);
    try {
      await login(name.trim());
      onSuccess();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
      <div className="bg-gray-800 rounded-lg p-6 w-full max-w-sm shadow-xl">
        <h2 className="text-xl font-bold mb-4">Join Tavoliere</h2>
        <form onSubmit={handleSubmit}>
          <label className="block text-sm text-gray-300 mb-1">
            Display Name
          </label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded text-white focus:outline-none focus:border-blue-500"
            placeholder="Your name"
            autoFocus
            maxLength={32}
          />
          {error && <p className="text-red-400 text-sm mt-2">{error}</p>}
          <div className="flex gap-3 mt-4 justify-end">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-gray-400 hover:text-white"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading || !name.trim()}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 rounded font-medium"
            >
              {loading ? "Joining..." : "Play"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
