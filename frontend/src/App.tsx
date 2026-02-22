import { BrowserRouter, Routes, Route } from "react-router-dom";
import { AuthProvider } from "./state/AuthContext";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { LandingPage } from "./pages/LandingPage";
import { LobbyPage } from "./pages/LobbyPage";
import { TablePage } from "./pages/TablePage";
import { SpectatorPage } from "./pages/SpectatorPage";
import { ReplayPage } from "./pages/ReplayPage";
import { GameLogPage } from "./pages/GameLogPage";
import { PostGameSummary } from "./pages/PostGameSummary";
import { ApiKeysPage } from "./pages/ApiKeysPage";
import { ProfilePage } from "./pages/ProfilePage";
import { AdminPage } from "./pages/AdminPage";
import { DataExplorerPage } from "./pages/DataExplorerPage";

export default function App() {
  return (
    <ErrorBoundary>
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/lobby" element={<LobbyPage />} />
          <Route path="/table/:tableId" element={<TablePage />} />
          <Route path="/spectate/:tableId" element={<SpectatorPage />} />
          <Route path="/replay/:tableId" element={<ReplayPage />} />
          <Route path="/games" element={<GameLogPage />} />
          <Route path="/table/:tableId/summary" element={<PostGameSummary />} />
          <Route path="/api-keys" element={<ApiKeysPage />} />
          <Route path="/profile" element={<ProfilePage />} />
          <Route path="/admin" element={<AdminPage />} />
          <Route path="/research/explorer" element={<DataExplorerPage />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
    </ErrorBoundary>
  );
}
