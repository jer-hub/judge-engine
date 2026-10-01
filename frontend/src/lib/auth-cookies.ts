import { cookies } from "next/headers";
import type { NextRequest, NextResponse } from "next/server";

const ACCESS = "je_access";
const REFRESH = "je_refresh";

export function accessCookieName() {
  return ACCESS;
}

export function refreshCookieName() {
  return REFRESH;
}

export function cookieOptions(maxAge: number) {
  // Secure by default in production; allow explicit override for local HTTP.
  const secure =
    process.env.JWT_COOKIE_SECURE === "true" ||
    (process.env.JWT_COOKIE_SECURE !== "false" &&
      process.env.NODE_ENV === "production");
  return {
    httpOnly: true,
    secure,
    sameSite: "lax" as const,
    path: "/",
    maxAge,
  };
}

// Match the backend's SIMPLE_JWT lifetimes (same env names as the backend).
function accessMaxAge() {
  return Number(process.env.JWT_ACCESS_MINUTES || 60) * 60;
}

function refreshMaxAge() {
  return Number(process.env.JWT_REFRESH_DAYS || 7) * 24 * 60 * 60;
}

export type TokenPair = { access: string; refresh: string };

export function setAuthCookies(response: NextResponse, tokens: TokenPair) {
  response.cookies.set(ACCESS, tokens.access, cookieOptions(accessMaxAge()));
  response.cookies.set(REFRESH, tokens.refresh, cookieOptions(refreshMaxAge()));
}

export function clearAuthCookies(response: NextResponse) {
  response.cookies.set(ACCESS, "", cookieOptions(0));
  response.cookies.set(REFRESH, "", cookieOptions(0));
}

export async function getAccessToken() {
  const jar = await cookies();
  return jar.get(ACCESS)?.value || null;
}

export async function getRefreshToken() {
  const jar = await cookies();
  return jar.get(REFRESH)?.value || null;
}

/**
 * Client IP to pass on to Django's throttles. Behind Caddy this is the
 * address Caddy saw; with no proxy in front, Next fills the header from the
 * socket (a client could spoof it there, which the per-username login
 * throttle still caps).
 */
export function clientIp(req: NextRequest): string | null {
  const xff = req.headers.get("x-forwarded-for");
  const last = xff?.split(",").pop()?.trim();
  return last || null;
}

export function forwardedHeaders(ip: string | null, init?: HeadersInit) {
  const headers = new Headers(init);
  if (ip) headers.set("X-Forwarded-For", ip);
  return headers;
}

// Refresh tokens rotate and the old one is blacklisted, so parallel requests
// that all hit an expired access token must share one refresh call. The
// result is kept briefly for requests that arrive just after it settles.
const REFRESH_REUSE_MS = 10_000;

/** `invalid`: the backend rejected the refresh token (session is over).
 *  `error`: network/5xx/429 — keep the cookies and let the user retry. */
export type RefreshResult =
  | { ok: true; tokens: TokenPair }
  | { ok: false; reason: "invalid" | "error" };

const inflight = new Map<string, Promise<RefreshResult>>();

export function refreshTokens(
  refresh: string,
  ip: string | null,
): Promise<RefreshResult> {
  let pending = inflight.get(refresh);
  if (!pending) {
    pending = (async (): Promise<RefreshResult> => {
      const res = await fetch(`${backendBase()}/api/auth/refresh/`, {
        method: "POST",
        headers: forwardedHeaders(ip, { "Content-Type": "application/json" }),
        body: JSON.stringify({ refresh }),
        cache: "no-store",
      });
      if (res.status === 401) return { ok: false, reason: "invalid" };
      if (!res.ok) return { ok: false, reason: "error" };
      const data = await res.json();
      // With ROTATE_REFRESH_TOKENS the response carries a new refresh token;
      // keeping the old one would make the next refresh fail.
      return {
        ok: true,
        tokens: {
          access: data.access as string,
          refresh: (data.refresh as string | undefined) ?? refresh,
        },
      };
    })().catch((): RefreshResult => ({ ok: false, reason: "error" }));
    inflight.set(refresh, pending);
    setTimeout(() => inflight.delete(refresh), REFRESH_REUSE_MS);
  }
  return pending;
}

export function backendBase() {
  return (
    process.env.INTERNAL_API_URL ||
    process.env.NEXT_PUBLIC_API_URL ||
    "http://localhost:8000"
  );
}
