/**
 * Google OAuth2 authentication.
 *
 * Auth is enabled only when NEXT_PUBLIC_GOOGLE_CLIENT_ID is set.
 * Without it the app runs unauthenticated (local dev).
 *
 * Tokens are stored in HttpOnly cookies set by the backend —
 * JS never touches the raw credential.
 */

const clientId = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID ?? "";

export const AUTH_ENABLED = Boolean(clientId);
export const googleClientId = clientId;

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export interface UserInfo {
  sub: string;
  name: string;
  email: string;
  picture: string;
}

export async function loginWithGoogle(idToken: string): Promise<UserInfo> {
  const res = await fetch(`${API_URL}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ id_token: idToken }),
  });
  if (!res.ok) {
    throw new Error("Login failed");
  }
  return (await res.json()) as UserInfo;
}

export async function logoutSession(): Promise<void> {
  await fetch(`${API_URL}/api/auth/logout`, {
    method: "POST",
    credentials: "include",
  });
}

export async function fetchMe(): Promise<UserInfo | null> {
  if (!AUTH_ENABLED) return null;
  const res = await fetch(`${API_URL}/api/auth/me`, {
    credentials: "include",
  });
  if (!res.ok) return null;
  return (await res.json()) as UserInfo;
}
