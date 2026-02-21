import { useAuth } from "../../hooks/useAuth";
import { Link } from "react-router-dom";

export function Header() {
  const { isAuthenticated, identity, logout } = useAuth();

  return (
    <header className="flex items-center justify-between px-6 py-3 bg-gray-800 border-b border-gray-700">
      <Link to="/" className="text-xl font-bold hover:text-blue-400">
        Tavoliere
      </Link>
      {isAuthenticated && identity && (
        <div className="flex items-center gap-4">
          <Link to="/lobby" className="text-sm text-gray-400 hover:text-white">
            Lobby
          </Link>
          <Link to="/games" className="text-sm text-gray-400 hover:text-white">
            My Games
          </Link>
          <Link to="/api-keys" className="text-sm text-gray-400 hover:text-white">
            API Keys
          </Link>
          <Link to="/profile" className="text-sm text-gray-400 hover:text-white">
            Profile
          </Link>
          <Link to="/admin" className="text-sm text-gray-400 hover:text-white">
            Admin
          </Link>
          <Link to="/research/explorer" className="text-sm text-gray-400 hover:text-white">
            Research
          </Link>
          <span className="text-gray-300 text-sm">{identity.display_name}</span>
          <button
            onClick={logout}
            className="text-sm text-gray-400 hover:text-white"
          >
            Logout
          </button>
        </div>
      )}
    </header>
  );
}
