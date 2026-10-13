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
export function downloadStandingsCsv(contestId: number, section?: string) {
  const query = section ? `?section=${encodeURIComponent(section)}` : "";
  return downloadFile(
    `/contests/${contestId}/standings-export${query}`,
    `contest-${contestId}-standings.csv`,
  );
}

/**
 * Every submitted solution for a contest and/or problem as a ZIP: .java files
 * per student and problem, plus index.csv (optionally one class section).
 */
export function downloadSolutionsZip(scope: { contest?: number; problem?: number; section?: string }) {
  const params = new URLSearchParams();
  if (scope.contest != null) params.set("contest", String(scope.contest));
  if (scope.problem != null) params.set("problem", String(scope.problem));
  if (scope.section) params.set("section", scope.section);
  return downloadFile(`/submissions/export?${params}`, "solutions.zip");
}

/** GET a file through the API proxy and save it with the server's filename. */
async function downloadFile(path: string, fallbackName: string) {
  const res = await fetch(`/api/proxy${path}`, { credentials: "include" });
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    const detail = body && typeof body === "object" && "detail" in body ? String(body.detail) : "";
    throw new Error(detail || `Download failed (HTTP ${res.status}).`);
  }
  const blob = await res.blob();
  const name =
    /filename="([^"]+)"/.exec(res.headers.get("Content-Disposition") ?? "")?.[1] ?? fallbackName;
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
