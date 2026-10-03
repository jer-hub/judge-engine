import { apiFetch } from "@/lib/api";

export type BulkRejudgeResult = { queued: number; skipped_in_flight: number };

/** Re-judge every finished submission to a problem and/or contest. */
export function bulkRejudge(scope: { problem?: number; contest?: number }) {
  return apiFetch<BulkRejudgeResult>("/submissions/bulk-rejudge/", {
    method: "POST",
    body: JSON.stringify(scope),
  });
}

export function describeRejudge(result: BulkRejudgeResult): string {
  const queued = `${result.queued} submission${result.queued === 1 ? "" : "s"} queued for re-judging`;
  return result.skipped_in_flight
    ? `${queued}; ${result.skipped_in_flight} already in the queue were left as they are.`
    : `${queued}.`;
}

/** Download a contest's final standings as CSV (optionally one section). */
export async function downloadStandingsCsv(contestId: number, section?: string) {
  const query = section ? `?section=${encodeURIComponent(section)}` : "";
  const res = await fetch(`/api/proxy/contests/${contestId}/standings-export${query}`, {
    credentials: "include",
  });
  if (!res.ok) throw new Error(`Export failed (HTTP ${res.status}).`);
  const blob = await res.blob();
  const name =
    /filename="([^"]+)"/.exec(res.headers.get("Content-Disposition") ?? "")?.[1] ??
    `contest-${contestId}-standings.csv`;
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = name;
  document.body.appendChild(link);
  link.click();
  link.remove();
  // Revoking right after click() can cancel the download in some browsers.
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export function djangoAdminUrl(path = "") {
  // Empty in the prod build: Caddy serves /admin/ on the same origin.
  const base = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
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
