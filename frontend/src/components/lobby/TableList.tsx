import { useNavigate } from "react-router-dom";
import type { TableSummary } from "../../types/models";

interface Props {
  tables: TableSummary[];
  onJoin: (tableId: string) => void;
}

export function TableList({ tables, onJoin }: Props) {
  const navigate = useNavigate();
  if (tables.length === 0) {
    return (
      <p className="text-gray-500 text-center py-8">
        No tables yet. Create one to get started.
      </p>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-gray-400 border-b border-gray-700">
            <th className="text-left py-2 px-3">Name</th>
            <th className="text-left py-2 px-3">Deck</th>
            <th className="text-center py-2 px-3">Seats</th>
            <th className="text-center py-2 px-3">Research</th>
            <th className="py-2 px-3"></th>
          </tr>
        </thead>
        <tbody>
          {tables.map((t) => (
            <tr
              key={t.table_id}
              className="border-b border-gray-800 hover:bg-gray-800/50"
            >
              <td className="py-2 px-3 font-medium">{t.display_name}</td>
              <td className="py-2 px-3 text-gray-400">
                {t.deck_recipe.replace(/_/g, " ")}
              </td>
              <td className="py-2 px-3 text-center">
                {t.seat_count}/{t.max_seats}
              </td>
              <td className="py-2 px-3 text-center">
                {t.research_mode && (
                  <span className="text-xs bg-purple-600/30 text-purple-300 px-2 py-0.5 rounded">
                    research
                  </span>
                )}
              </td>
              <td className="py-2 px-3 text-right flex gap-1 justify-end">
                {t.seat_count >= t.max_seats ? (
                  <button
                    onClick={() => navigate(`/spectate/${t.table_id}`)}
                    className="px-3 py-1 bg-yellow-600 hover:bg-yellow-500 rounded text-xs font-medium"
                  >
                    Spectate
                  </button>
                ) : (
                  <button
                    onClick={() => onJoin(t.table_id)}
                    className="px-3 py-1 bg-blue-600 hover:bg-blue-500 rounded text-xs font-medium"
                  >
                    Join
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
