import React, { createContext, useContext, useState, useCallback } from "react";
import { setUnauthorizedHandler } from "../lib/api";

const TOKEN_STORAGE_KEY = "access_token";

interface AuthContextType {
  token: string | null;
  login: (token: string) => void;
  logout: () => void;
  isAuthenticated: boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({
  children,
}) => {
  const [token, setToken] = useState<string | null>(() =>
    typeof window !== "undefined"
      ? localStorage.getItem(TOKEN_STORAGE_KEY)
      : null,
  );

  const login = useCallback((newToken: string) => {
    localStorage.setItem(TOKEN_STORAGE_KEY, newToken);
    setToken(newToken);
  }, []);

  const logout = useCallback(() => {
    try {
      localStorage.removeItem(TOKEN_STORAGE_KEY);
    } catch {
      /* storage may be unavailable (private mode) */
    }
    setToken(null);
  }, []);

  // A 401 from any request means the token is expired or rejected. Clear it so
  // the app stops treating the user as signed in, rather than leaving them on a
  // permanently erroring screen. The route guards then send them to /login.
  React.useEffect(() => {
    setUnauthorizedHandler(() => {
      setToken(null);
    });
    return () => setUnauthorizedHandler(null);
  }, []);

  return (
    <AuthContext.Provider
      value={{
        token,
        login,
        logout,
        isAuthenticated: token !== null,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = (): AuthContextType => {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return ctx;
};
