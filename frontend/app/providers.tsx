"use client";

import { GoogleOAuthProvider } from "@react-oauth/google";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createContext, useContext, useEffect, useState } from "react";

import {
  AUTH_ENABLED,
  fetchMe,
  googleClientId,
  loginWithGoogle,
  logoutSession,
} from "@/lib/auth";
import type { UserInfo } from "@/lib/auth";

interface AuthContextValue {
  user: { name: string; email: string; picture: string } | null;
  login: (idToken: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue>({
  user: null,
  login: async () => {},
  logout: () => {},
});

export function useAuthContext() {
  return useContext(AuthContext);
}

function AuthContextProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthContextValue["user"]>(null);

  useEffect(() => {
    fetchMe()
      .then((info) => {
        if (info) setUser({ name: info.name, email: info.email, picture: info.picture });
      })
      .catch(() => {
        // Network error during session restore → stay logged out, no crash.
      });
  }, []);

  async function login(idToken: string) {
    const info: UserInfo = await loginWithGoogle(idToken);
    setUser({ name: info.name, email: info.email, picture: info.picture });
  }

  function logout() {
    // Clear UI immediately; the cookie-clearing request is best-effort.
    setUser(null);
    void logoutSession().catch(() => {});
  }

  return (
    <AuthContext.Provider value={{ user, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: { queries: { refetchOnWindowFocus: false, staleTime: 5_000 } },
      }),
  );

  const inner = (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );

  if (!AUTH_ENABLED) return inner;

  return (
    <GoogleOAuthProvider clientId={googleClientId}>
      <AuthContextProvider>{inner}</AuthContextProvider>
    </GoogleOAuthProvider>
  );
}
