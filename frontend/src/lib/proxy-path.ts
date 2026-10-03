// "." / ".." would walk out of /api/ once fetch() normalises the URL, and
// separators or escapes inside one decoded segment ("..%2Fadmin") would too.
// eslint-disable-next-line no-control-regex
const UNSAFE_SEGMENT = /[/\\%?#\u0000-\u001f\u007f]/;

/**
 * The Django URL for a proxied request, or null if the path could reach
 * anything outside /api/. Django's APPEND_SLASH cannot redirect a POST while
 * keeping its body, so the path always ends in a slash.
 */
export function backendApiUrl(base: string, parts: string[], search = ""): string | null {
  if (parts.some((p) => p === "" || p === "." || p === ".." || UNSAFE_SEGMENT.test(p))) {
    return null;
  }
  const path = parts.map(encodeURIComponent).join("/");
  const url = new URL(`${base.replace(/\/$/, "")}/api/${path ? `${path}/` : ""}${search}`);
  if (!url.pathname.startsWith("/api/")) return null;
  return url.toString();
}
