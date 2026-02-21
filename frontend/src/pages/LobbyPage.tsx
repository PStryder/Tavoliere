import { useEffect, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import { PageLayout } from "../components/layout/PageLayout";
import { TableList } from "../components/lobby/TableList";
import { CreateTableModal } from "../components/lobby/CreateTableModal";
import { listTables, joinTable } from "../api/tables";
import type { TableSummary } from "../types/models";

export function LobbyPage() {
  const { isAuthenticated, identity } = useAuth();
  const navigate = useNavigate();
  const [tables, setTables] = useState<TableSummary[]>([]);
  const [showCreate, setShowCreate] = useState(false);
  const [loading, setLoading] = useState(true);

  const fetchTables = useCallback(async () => {
    try {
      const data = await listTables();
      setTables(data);
    } catch {
      /* retry later */
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!isAuthenticated) {
      navigate("/");
      return;
    }
    fetchTables();
  }, [isAuthenticated, navigate, fetchTables]);

  async function handleJoin(tableId: string) {
    if (!identity) return;
    try {
      await joinTable(tableId, identity.display_name);
      navigate(`/table/${tableId}`);
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to join");
    }
  }

  async function handleCreated(tableId: string) {
    setShowCreate(false);
    if (!identity) return;
    try {
      await joinTable(tableId, identity.display_name);
      navigate(`/table/${tableId}`);
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to join created table");
    }
  }

  return (
    <PageLayout>
      <div className="max-w-3xl mx-auto px-4 py-8">
        <div className="flex items-center justify-between mb-6">
          <h1 className="text-2xl font-bold">Lobby</h1>
          <div className="flex gap-3">
            <button
              onClick={fetchTables}
              className="px-3 py-1.5 text-sm bg-gray-700 hover:bg-gray-600 rounded"
            >
              Refresh
            </button>
            <button
              onClick={() => setShowCreate(true)}
              className="px-3 py-1.5 text-sm bg-blue-600 hover:bg-blue-500 rounded font-medium"
            >
              Create Table
            </button>
          </div>
        </div>

        {loading ? (
          <p className="text-gray-500 text-center py-8">Loading...</p>
        ) : (
          <TableList tables={tables} onJoin={handleJoin} />
        )}
      </div>

      {showCreate && (
        <CreateTableModal
          onClose={() => setShowCreate(false)}
          onCreated={handleCreated}
        />
      )}
    </PageLayout>
  );
}
