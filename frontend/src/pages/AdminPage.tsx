import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import { Header } from "../components/layout/Header";
import { UserManager } from "../components/admin/UserManager";
import { ApiKeyAdmin } from "../components/admin/ApiKeyAdmin";
import { ConventionTemplateEditor } from "../components/admin/ConventionTemplateEditor";
import { ResearchDashboard } from "../components/admin/ResearchDashboard";

type Tab = "users" | "keys" | "conventions" | "research";

const tabs: { id: Tab; label: string }[] = [
  { id: "users", label: "Users" },
  { id: "keys", label: "API Keys" },
  { id: "conventions", label: "Conventions" },
  { id: "research", label: "Research" },
];

export function AdminPage() {
  const navigate = useNavigate();
  const { isAuthenticated } = useAuth();
  const [activeTab, setActiveTab] = useState<Tab>("users");

  useEffect(() => {
    if (!isAuthenticated) {
      navigate("/");
    }
  }, [isAuthenticated, navigate]);

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      <Header />
      <div className="max-w-4xl mx-auto px-6 py-8">
        <h1 className="text-2xl font-bold mb-6">Admin</h1>

        {/* Tab bar */}
        <div className="flex gap-1 mb-6 border-b border-gray-700">
          {tabs.map((t) => (
            <button
              key={t.id}
              onClick={() => setActiveTab(t.id)}
              className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${
                activeTab === t.id
                  ? "border-blue-500 text-white"
                  : "border-transparent text-gray-400 hover:text-white"
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>

        {/* Tab content */}
        {activeTab === "users" && <UserManager />}
        {activeTab === "keys" && <ApiKeyAdmin />}
        {activeTab === "conventions" && <ConventionTemplateEditor />}
        {activeTab === "research" && <ResearchDashboard />}
      </div>
    </div>
  );
}
