import { createContext, ReactNode, useContext, useEffect, useMemo, useState } from "react";

import { getMe, getStoredToken, login as loginRequest, setStoredToken, UserPublic } from "../api/client";

type AuthContextValue = {
  token: string | null;
  user: UserPublic | null;
  loading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(() => getStoredToken());
  const [user, setUser] = useState<UserPublic | null>(null);
  const [loading, setLoading] = useState(Boolean(token));

  useEffect(() => {
    let active = true;
    if (!token) {
      setUser(null);
      setLoading(false);
      return;
    }
    setLoading(true);
    getMe()
      .then((currentUser) => {
        if (active) {
          setUser(currentUser);
        }
      })
      .catch(() => {
        if (active) {
          setStoredToken(null);
          setToken(null);
          setUser(null);
        }
      })
      .finally(() => {
        if (active) {
          setLoading(false);
        }
      });
    return () => {
      active = false;
    };
  }, [token]);

  const value = useMemo<AuthContextValue>(
    () => ({
      token,
      user,
      loading,
      login: async (username: string, password: string) => {
        const response = await loginRequest(username, password);
        setStoredToken(response.access_token);
        setToken(response.access_token);
        setUser(response.user);
      },
      logout: () => {
        setStoredToken(null);
        setToken(null);
        setUser(null);
      }
    }),
    [loading, token, user]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth debe usarse dentro de AuthProvider");
  }
  return context;
}
