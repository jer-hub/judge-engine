import type { ActiveContestRef } from "@/lib/types";

export function problemHref(
  slug: string,
  contestId?: number | string | null,
): string {
  if (contestId !== null && contestId !== undefined && contestId !== "") {
    return `/problems/${slug}?contest=${encodeURIComponent(String(contestId))}`;
  }
  return `/problems/${slug}`;
}

export function missingContestTargets(
  contestQueryParam: string | null,
  activeContests?: ActiveContestRef[] | null,
): ActiveContestRef[] {
  if (contestQueryParam) return [];
  if (!activeContests || activeContests.length === 0) return [];
  return activeContests;
}
