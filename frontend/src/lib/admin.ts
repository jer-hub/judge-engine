export function djangoAdminUrl(path = "") {
  const base = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  return `${base.replace(/\/$/, "")}/admin/${path}`;
}

/** Flatten DRF validation errors into a short operator-facing message. */
export function formatApiErrorPayload(payload: unknown, fallback: string): string {
  if (!payload || typeof payload !== "object") return fallback;
  const entries = Object.entries(payload as Record<string, unknown>);
  if (entries.length === 0) return fallback;
  const messages = entries.map(([field, value]) => {
    if (Array.isArray(value)) return `${field}: ${value.join(", ")}`;
    if (typeof value === "string") return `${field}: ${value}`;
    return `${field}: ${JSON.stringify(value)}`;
  });
  return messages.join(" · ") || fallback;
}
