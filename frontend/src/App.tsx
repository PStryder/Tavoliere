import { BrowserRouter, Routes, Route } from "react-router-dom";
import { AuthProvider } from "./state/AuthContext";
import { LandingPage } from "./pages/LandingPage";
import { LobbyPage } from "./pages/LobbyPage";
import { TablePage } from "./pages/TablePage";

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route path="/lobby" element={<LobbyPage />} />
          <Route path="/table/:tableId" element={<TablePage />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
