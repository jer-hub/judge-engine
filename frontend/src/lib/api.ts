const PUBLIC_API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  payload: unknown;

  constructor(message: string, status: number, payload: unknown) {
    super(message);
    this.status = status;
    this.payload = payload;
  }
}

const FIELD_LABELS: Record<string, string> = {
  source_code: "Code",
  stdin: "Input",
};

function fieldLabel(field: string) {
  const label = FIELD_LABELS[field] ?? field.replace(/_/g, " ");
  return label.charAt(0).toUpperCase() + label.slice(1);
}

/**
 * A readable message from a DRF error body. Validation errors arrive keyed by
 * field ({"contest": ["Submissions are only allowed during the contest
 * window."]}), not as {"detail": ...}; without this the user saw only the
 * status text, "Bad Request".
 */
export function apiErrorMessage(data: unknown): string | null {
  if (!data || typeof data !== "object" || Array.isArray(data)) return null;
  const parts: string[] = [];
  for (const [field, value] of Object.entries(data as Record<string, unknown>)) {
    const text = (Array.isArray(value) ? value : [value])
      .map((v) => (typeof v === "string" ? v : JSON.stringify(v)))
      .join(" ");
    if (!text) continue;
    parts.push(field === "detail" || field === "non_field_errors" ? text : `${fieldLabel(field)}: ${text}`);
  }
  return parts.length ? parts.join(" ") : null;
}

async function parseJson(res: Response) {
  const text = await res.text();
  if (!text) return null;
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

/**
 * The session is gone (the proxy could not refresh it): send the user to log
 * in and come back here, instead of every page showing a raw 401 message.
 */
function redirectToLogin() {
  if (typeof window === "undefined") return;
  const { pathname, search } = window.location;
  // On /login itself a 401 is expected (the NavBar's "me" probe).
  if (pathname === "/login") return;
  window.location.assign(`/login?next=${encodeURIComponent(pathname + search)}`);
}

/** Browser-side API helper that goes through Next.js auth cookie proxy when needed. */
export async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const headers = new Headers(options.headers || {});
  if (!headers.has("Content-Type") && options.body) {
    headers.set("Content-Type", "application/json");
  }

  // Next 308-redirects "/api/proxy/x/" to "/api/proxy/x" (a wasted round
  // trip per call); the proxy adds the slash back for Django.
  const q = path.indexOf("?");
  const pathname = q === -1 ? path : path.slice(0, q);
  const query = q === -1 ? "" : path.slice(q);
  const proxyPath = pathname.replace(/\/+$/, "") + query;

  const res = await fetch(`/api/proxy${proxyPath}`, {
    ...options,
    headers,
    credentials: "include",
  });

  const data = await parseJson(res);
  if (res.status === 401) redirectToLogin();
  if (!res.ok) {
    let detail = apiErrorMessage(data);
    if (!detail && typeof data === "string" && data.includes("APPEND_SLASH")) {
      detail = "API URL missing trailing slash (fixed — please retry).";
    }
    throw new ApiError(detail || res.statusText || `HTTP ${res.status}`, res.status, data);
  }
  return data as T;
}

export function publicApiBase() {
  return PUBLIC_API;
}
