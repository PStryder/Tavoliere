import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth";
import { LoginModal } from "../components/auth/LoginModal";

export function LandingPage() {
  const { isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const [showLogin, setShowLogin] = useState(false);

  function handlePlay() {
    if (isAuthenticated) {
      navigate("/lobby");
    } else {
      setShowLogin(true);
    }
  }

  return (
    <div className="min-h-screen flex flex-col items-center justify-center">
      <h1 className="text-5xl font-bold mb-4">Tavoliere</h1>
      <p className="text-gray-400 text-lg mb-8">
        A rule-agnostic virtual card table
      </p>
      <button
        onClick={handlePlay}
        className="px-8 py-3 bg-blue-600 hover:bg-blue-500 rounded-lg text-lg font-semibold transition-colors"
      >
        Play
      </button>

      {showLogin && (
        <LoginModal
          onClose={() => setShowLogin(false)}
          onSuccess={() => navigate("/lobby")}
        />
      )}
    </div>
  );
}
