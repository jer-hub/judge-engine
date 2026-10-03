const FALLBACK = "/problems";

/**
 * Where to go after login: a path on this site only (no open redirect).
 *
 * Resolved the way the browser will resolve it, so tricks that string checks
 * miss (tabs/newlines the URL parser strips, "/\host", "//host") cannot turn
 * it into another origin.
 */
export function safeNextPath(next: string | null, origin: string): string {
  if (!next || !next.startsWith("/")) return FALLBACK;
  let url: URL;
  try {
    url = new URL(next, origin);
  } catch {
    return FALLBACK;
  }
  if (url.origin !== new URL(origin).origin) return FALLBACK;
  if (url.pathname === "/login" || url.pathname.startsWith("/login/")) return FALLBACK;
  return `${url.pathname}${url.search}${url.hash}`;
}
