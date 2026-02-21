import { useEffect, useState } from "react";
import {
  listConventions,
  createConvention,
  deleteConvention,
} from "../../api/conventions";
import type { ConventionTemplate } from "../../types/models";

export function ConventionTemplateEditor() {
  const [templates, setTemplates] = useState<ConventionTemplate[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({
    name: "",
    deck_recipe: "standard_52",
    seat_count: 4,
    suggested_phases: "",
    notes: "",
  });
  const [creating, setCreating] = useState(false);
  const [expanded, setExpanded] = useState<string | null>(null);

  useEffect(() => {
    load();
  }, []);

  function load() {
    listConventions()
      .then(setTemplates)
      .catch(() => {})
      .finally(() => setLoading(false));
  }

  async function handleCreate() {
    if (!form.name.trim()) return;
    setCreating(true);
    try {
      const phases = form.suggested_phases
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean);
      const notes: Record<string, string> = {};
      if (form.notes.trim()) {
        for (const line of form.notes.split("\n")) {
          const idx = line.indexOf(":");
          if (idx > 0) {
            notes[line.slice(0, idx).trim()] = line.slice(idx + 1).trim();
          }
        }
      }
      await createConvention({
        name: form.name.trim(),
        deck_recipe: form.deck_recipe,
        seat_count: form.seat_count,
        suggested_phases: phases,
        notes,
      });
      setShowForm(false);
      setForm({ name: "", deck_recipe: "standard_52", seat_count: 4, suggested_phases: "", notes: "" });
      load();
    } catch {
      /* empty */
    } finally {
      setCreating(false);
    }
  }

  async function handleDelete(id: string, name: string) {
    if (!confirm(`Delete convention "${name}"?`)) return;
    try {
      await deleteConvention(id);
      load();
    } catch {
      /* empty */
    }
  }

  if (loading) return <p className="text-gray-500 py-4">Loading...</p>;

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <p className="text-sm text-gray-400">
          {templates.length} template{templates.length !== 1 ? "s" : ""}
        </p>
        <button
          onClick={() => setShowForm(!showForm)}
          className="px-3 py-1.5 bg-blue-600 hover:bg-blue-500 rounded text-xs font-medium"
        >
          {showForm ? "Cancel" : "New Template"}
        </button>
      </div>

      {showForm && (
        <div className="bg-gray-800/50 rounded-lg p-4 mb-4 space-y-3">
          <input
            type="text"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            placeholder="Template name"
            className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded text-sm focus:outline-none focus:border-blue-500"
          />
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs text-gray-500">Deck Recipe</label>
              <select
                value={form.deck_recipe}
                onChange={(e) => setForm({ ...form, deck_recipe: e.target.value })}
                className="w-full mt-1 px-3 py-2 bg-gray-700 border border-gray-600 rounded text-sm"
              >
                <option value="standard_52">Standard 52</option>
                <option value="euchre_24">Euchre 24</option>
                <option value="pinochle_48">Pinochle 48</option>
                <option value="pinochle_80">Pinochle 80</option>
              </select>
            </div>
            <div>
              <label className="text-xs text-gray-500">Seat Count</label>
              <input
                type="number"
                value={form.seat_count}
                onChange={(e) => setForm({ ...form, seat_count: Number(e.target.value) })}
                min={2}
                max={8}
                className="w-full mt-1 px-3 py-2 bg-gray-700 border border-gray-600 rounded text-sm"
              />
            </div>
          </div>
          <div>
            <label className="text-xs text-gray-500">Phases (comma-separated)</label>
            <input
              type="text"
              value={form.suggested_phases}
              onChange={(e) => setForm({ ...form, suggested_phases: e.target.value })}
              placeholder="Deal, Bid, Play, Score"
              className="w-full mt-1 px-3 py-2 bg-gray-700 border border-gray-600 rounded text-sm focus:outline-none focus:border-blue-500"
            />
          </div>
          <div>
            <label className="text-xs text-gray-500">Notes (Key: Value per line)</label>
            <textarea
              value={form.notes}
              onChange={(e) => setForm({ ...form, notes: e.target.value })}
              placeholder={"Bidding: Description here\nScoring: Description here"}
              rows={3}
              className="w-full mt-1 px-3 py-2 bg-gray-700 border border-gray-600 rounded text-sm focus:outline-none focus:border-blue-500 resize-none"
            />
          </div>
          <button
            onClick={handleCreate}
            disabled={creating || !form.name.trim()}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:bg-gray-600 rounded text-sm font-medium"
          >
            {creating ? "Creating..." : "Create Template"}
          </button>
        </div>
      )}

      <div className="space-y-2">
        {templates.map((t) => (
          <div key={t.template_id} className="bg-gray-800/50 rounded-lg px-4 py-3">
            <div className="flex items-center justify-between">
              <div
                className="flex-1 cursor-pointer"
                onClick={() => setExpanded(expanded === t.template_id ? null : t.template_id)}
              >
                <div className="flex items-center gap-2">
                  <span className="font-medium text-sm">{t.name}</span>
                  {t.built_in && (
                    <span className="text-xs bg-gray-600/50 text-gray-400 px-1.5 py-0.5 rounded">
                      built-in
                    </span>
                  )}
                </div>
                <div className="text-xs text-gray-500">
                  {t.deck_recipe.replace(/_/g, " ")} · {t.seat_count} seats ·{" "}
                  {t.suggested_phases.join(" → ")}
                </div>
              </div>
              {!t.built_in && (
                <button
                  onClick={() => handleDelete(t.template_id, t.name)}
                  className="px-3 py-1 text-xs bg-red-600/20 text-red-400 hover:bg-red-600/40 rounded"
                >
                  Delete
                </button>
              )}
            </div>
            {expanded === t.template_id && Object.keys(t.notes).length > 0 && (
              <div className="mt-3 pt-3 border-t border-gray-700 space-y-2">
                {Object.entries(t.notes).map(([key, value]) => (
                  <div key={key}>
                    <span className="text-xs font-semibold text-gray-400">{key}:</span>
                    <p className="text-xs text-gray-500 mt-0.5">{value}</p>
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
