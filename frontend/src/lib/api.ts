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

async function parseJson(res: Response) {
  const text = await res.text();
  if (!text) return null;
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
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

  const res = await fetch(`/api/proxy${path}`, {
    ...options,
    headers,
    credentials: "include",
  });

  const data = await parseJson(res);
  if (!res.ok) {
    let detail: string | null = null;
    if (data && typeof data === "object" && data !== null && "detail" in data) {
      detail = String((data as { detail: unknown }).detail);
    } else if (typeof data === "string" && data.includes("APPEND_SLASH")) {
      detail = "API URL missing trailing slash (fixed — please retry).";
    }
    throw new ApiError(detail || res.statusText || `HTTP ${res.status}`, res.status, data);
  }
  return data as T;
}

export function publicApiBase() {
  return PUBLIC_API;
}
