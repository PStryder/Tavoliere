import {
  createContext,
  useReducer,
  useCallback,
  type ReactNode,
} from "react";
import { bootstrap, getToken } from "../api/auth";
import { setToken } from "../api/client";
import type { CredentialWithSecret } from "../types/models";

export interface AuthState {
  token: string | null;
  identity: { identity_id: string; effective_identity: string; display_name: string } | null;
  credentials: CredentialWithSecret[];
  isAuthenticated: boolean;
}

type AuthAction =
  | {
      type: "LOGIN";
      payload: {
        token: string;
        identity: { identity_id: string; effective_identity: string; display_name: string };
        credentials: CredentialWithSecret[];
      };
    }
  | { type: "LOGOUT" };

const initialState: AuthState = {
  token: null,
  identity: null,
  credentials: [],
  isAuthenticated: false,
};

function authReducer(_state: AuthState, action: AuthAction): AuthState {
  switch (action.type) {
    case "LOGIN":
      return {
        token: action.payload.token,
        identity: action.payload.identity,
        credentials: action.payload.credentials,
        isAuthenticated: true,
      };
    case "LOGOUT":
      return initialState;
  }
}

export interface AuthContextValue extends AuthState {
  login: (displayName: string) => Promise<void>;
  logout: () => void;
}

export const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(authReducer, initialState);

  const login = useCallback(async (displayName: string) => {
    const res = await bootstrap(displayName);
    if (!res.credentials?.length) {
      throw new Error("Bootstrap returned no credentials");
    }
    const cred = res.credentials[0];
    const tokenRes = await getToken(cred.client_id, cred.client_secret);
    setToken(tokenRes.access_token);
    // effective_identity mirrors backend TokenPayload.effective_identity:
    // AI credentials use credential_id, humans use principal identity_id.
    const effectiveId = cred.player_kind === "ai"
      ? cred.credential_id
      : res.principal.identity_id;
    dispatch({
      type: "LOGIN",
      payload: {
        token: tokenRes.access_token,
        identity: {
          identity_id: res.principal.identity_id,
          effective_identity: effectiveId,
          display_name: res.principal.display_name,
        },
        credentials: res.credentials,
      },
    });
  }, []);

  const logout = useCallback(() => {
    setToken(null);
    dispatch({ type: "LOGOUT" });
  }, []);

  return (
    <AuthContext.Provider value={{ ...state, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}
