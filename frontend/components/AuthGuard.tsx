"use client";

import { GoogleLogin } from "@react-oauth/google";
import Image from "next/image";

import { useAuthContext } from "@/app/providers";
import { AUTH_ENABLED } from "@/lib/auth";

/**
 * Wraps the app content. When auth is enabled:
 *  - logged-in users  → children
 *  - unauthenticated  → login screen with Google button
 *
 * When auth is disabled (NEXT_PUBLIC_GOOGLE_CLIENT_ID not set) → children directly.
 */
export function AuthGuard({ children }: { children: React.ReactNode }) {
  if (!AUTH_ENABLED) return <>{children}</>;
  return <AuthGate>{children}</AuthGate>;
}


function AuthGate({ children }: { children: React.ReactNode }) {
  const { user, login } = useAuthContext();

  if (user) return <>{children}</>;

  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-8 px-4">
      <Image
        src="/logo_azure.png"
        alt="Azure RAG Assistant"
        width={320}
        height={218}
        className="h-24 w-auto object-contain"
        priority
      />

      <div className="text-center">
        <h1 className="text-2xl font-semibold text-foreground">
          Azure RAG Assistant
        </h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Zaloguj się kontem Google, aby kontynuować.
        </p>
      </div>

      <GoogleLogin
        onSuccess={(response) => {
          if (response.credential) void login(response.credential);
        }}
        onError={() => {}}
        theme="filled_black"
        shape="pill"
        text="signin_with"
      />
    </div>
  );
}
