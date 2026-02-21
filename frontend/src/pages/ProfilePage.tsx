import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import { Header } from "../components/layout/Header";
import { getProfile, updateProfile, exportData, deleteAccount } from "../api/profile";
import type { ProfileInfo } from "../types/models";

export function ProfilePage() {
  const navigate = useNavigate();
  const { isAuthenticated, logout } = useAuth();
  const [profile, setProfile] = useState<ProfileInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(false);
  const [editName, setEditName] = useState("");
  const [saving, setSaving] = useState(false);
  const [exporting, setExporting] = useState(false);

  useEffect(() => {
    if (!isAuthenticated) {
      navigate("/");
      return;
    }
    getProfile()
      .then((p) => {
        setProfile(p);
        setEditName(p.display_name);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [isAuthenticated, navigate]);

  async function handleSave() {
    if (!editName.trim()) return;
    setSaving(true);
    try {
      const updated = await updateProfile(editName.trim());
      setProfile({ ...profile!, ...updated });
      setEditing(false);
    } catch {
      /* empty */
    } finally {
      setSaving(false);
    }
  }

  async function handleExport() {
    setExporting(true);
    try {
      const data = await exportData();
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "tavoliere-data-export.json";
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      /* empty */
    } finally {
      setExporting(false);
    }
  }

  async function handleDelete() {
    if (!confirm("Delete your account? This will revoke all API keys and remove your data. This cannot be undone.")) return;
    if (!confirm("Are you sure? Type the confirmation to proceed.")) return;
    try {
      await deleteAccount();
      logout();
      navigate("/");
    } catch {
      /* empty */
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-900 text-white">
        <Header />
        <div className="max-w-2xl mx-auto px-6 py-8">
          <p className="text-gray-500">Loading...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      <Header />
      <div className="max-w-2xl mx-auto px-6 py-8">
        <h1 className="text-2xl font-bold mb-6">Profile</h1>

        {profile && (
          <>
            {/* Identity Section */}
            <div className="bg-gray-800 rounded-lg p-5 mb-6">
              <h2 className="text-sm font-semibold text-gray-400 mb-4 uppercase tracking-wider">Identity</h2>
              <div className="space-y-3">
                <div>
                  <label className="text-xs text-gray-500">Display Name</label>
                  {editing ? (
                    <div className="flex gap-2 mt-1">
                      <input
                        type="text"
                        value={editName}
                        onChange={(e) => setEditName(e.target.value)}
                        className="flex-1 px-3 py-1.5 bg-gray-700 border border-gray-600 rounded text-sm focus:outline-none focus:border-blue-500"
                        onKeyDown={(e) => e.key === "Enter" && handleSave()}
                      />
                      <button
                        onClick={handleSave}
                        disabled={saving}
                        className="px-3 py-1.5 bg-blue-600 hover:bg-blue-500 rounded text-xs font-medium"
                      >
                        {saving ? "Saving..." : "Save"}
                      </button>
                      <button
                        onClick={() => { setEditing(false); setEditName(profile.display_name); }}
                        className="px-3 py-1.5 bg-gray-700 hover:bg-gray-600 rounded text-xs"
                      >
                        Cancel
                      </button>
                    </div>
                  ) : (
                    <div className="flex items-center gap-2 mt-1">
                      <span className="text-white">{profile.display_name}</span>
                      <button
                        onClick={() => setEditing(true)}
                        className="text-xs text-blue-400 hover:text-blue-300"
                      >
                        Edit
                      </button>
                    </div>
                  )}
                </div>
                <div>
                  <label className="text-xs text-gray-500">Identity ID</label>
                  <div className="text-sm text-gray-400 font-mono mt-1">{profile.identity_id}</div>
                </div>
                <div>
                  <label className="text-xs text-gray-500">Created</label>
                  <div className="text-sm text-gray-400 mt-1">
                    {new Date(profile.created_at).toLocaleDateString()}
                  </div>
                </div>
                <div>
                  <label className="text-xs text-gray-500">API Keys</label>
                  <div className="text-sm text-gray-400 mt-1">
                    {profile.credential_count} credential{profile.credential_count !== 1 ? "s" : ""}
                  </div>
                </div>
                {profile.is_admin && (
                  <div>
                    <span className="text-xs bg-purple-600/30 text-purple-300 px-2 py-0.5 rounded">
                      Admin
                    </span>
                  </div>
                )}
              </div>
            </div>

            {/* Data Rights Section */}
            <div className="bg-gray-800 rounded-lg p-5">
              <h2 className="text-sm font-semibold text-gray-400 mb-4 uppercase tracking-wider">Data Rights</h2>
              <div className="space-y-3">
                <button
                  onClick={handleExport}
                  disabled={exporting}
                  className="w-full py-2 bg-gray-700 hover:bg-gray-600 rounded text-sm font-medium"
                >
                  {exporting ? "Preparing export..." : "Export My Data"}
                </button>
                <button
                  onClick={handleDelete}
                  className="w-full py-2 bg-red-600/20 text-red-400 hover:bg-red-600/40 rounded text-sm font-medium"
                >
                  Delete My Account
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
