const COOKIE = "sf_client_id";
const SESSION_KEY = "sf_session_id";

export function getClientId(): string {
  if (typeof document === "undefined") return "";
  const match = document.cookie.match(new RegExp(`(?:^|; )${COOKIE}=([^;]*)`));
  if (match?.[1]) return match[1];
  const id = crypto.randomUUID();
  document.cookie = `${COOKIE}=${id}; path=/; max-age=31536000; SameSite=Lax`;
  return id;
}

export function getStoredSessionId(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(SESSION_KEY);
}

export function setStoredSessionId(id: string): void {
  localStorage.setItem(SESSION_KEY, id);
}
