"use client";

import Link from "next/link";
import { useMemo } from "react";
import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { EmptyState } from "@/components/EmptyState";
import { VerdictBadge } from "@/components/SubmissionStatus";
import { apiFetch } from "@/lib/api";
import { buildListQuery } from "@/lib/pagination";
import type { ContestListItem, Paginated, Submission } from "@/lib/types";

type Props = {
  contestId?: number | null;
  onContestFilterChange?: (contestId: number | null) => void;
};

export function SubmissionsPanel({
  contestId = null,
  onContestFilterChange,
}: Props) {
  const contests = useQuery({
    queryKey: ["admin", "contests", "submissions-filter"],
    queryFn: () =>
      apiFetch<Paginated<ContestListItem>>("/contests/?page_size=100"),
  });

  const queryPath = buildListQuery("/submissions/", {
    contest: contestId ?? undefined,
  });

  const { data, isLoading, error } = useQuery({
    queryKey: ["admin", "submissions", { contest: contestId }],
    queryFn: () => apiFetch<Paginated<Submission>>(queryPath),
    refetchInterval: 8000,
    placeholderData: keepPreviousData,
  });

  const contestOptions = useMemo(() => {
    const rows = contests.data?.results ?? [];
    return [...rows].sort((a, b) => a.title.localeCompare(b.title));
  }, [contests.data]);

  const selectedTitle =
    contestOptions.find((c) => c.id === contestId)?.title ??
    (contestId != null ? `Contest #${contestId}` : null);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <p className="text-sm text-slate-400">
          {contestId != null
            ? `Filtered to ${selectedTitle}. Auto-refreshes while this tab is open.`
            : "Platform-wide queue. Auto-refreshes every few seconds while this tab is open."}
        </p>
        <label className="block text-xs text-slate-400">
          Contest
          <select
            className="mt-1 block min-w-[200px] rounded-sm border border-slate-700 bg-slate-900 px-2 py-1.5 text-sm text-slate-200"
            value={contestId ?? ""}
            onChange={(e) => {
              const raw = e.target.value;
              onContestFilterChange?.(raw ? Number(raw) : null);
            }}
          >
            <option value="">All contests</option>
            {contestOptions.map((c) => (
              <option key={c.id} value={c.id}>
                {c.title}
                {c.is_archived ? " (archived)" : ""}
              </option>
            ))}
          </select>
        </label>
      </div>

      {isLoading && <p className="text-sm text-slate-400">Loading submissions…</p>}
      {error && <p className="text-sm text-red-300">{(error as Error).message}</p>}

      {!isLoading && (data?.results?.length ?? 0) === 0 ? (
        <EmptyState
          title="No submissions"
          body={
            contestId != null
              ? "Nothing for this contest yet."
              : "No submissions yet."
          }
        />
      ) : (
        <div className="overflow-x-auto rounded-xl border border-slate-800">
          <table className="w-full min-w-[720px] text-left text-sm">
            <thead className="bg-slate-900/80 text-slate-400">
              <tr>
                <th className="px-4 py-3 font-medium">ID</th>
                <th className="px-4 py-3 font-medium">User</th>
                <th className="px-4 py-3 font-medium">Problem</th>
                <th className="px-4 py-3 font-medium">Status</th>
                <th className="px-4 py-3 font-medium">Submitted</th>
              </tr>
            </thead>
            <tbody>
              {(data?.results ?? []).map((s) => (
                <tr
                  key={s.id}
                  className="border-t border-slate-800 hover:bg-slate-900/40"
                >
                  <td className="px-4 py-3 font-mono text-xs">
                    <Link
                      href={`/submissions/${s.id}`}
                      className="text-emerald-300 hover:underline"
                    >
                      #{s.id}
                    </Link>
                  </td>
                  <td className="px-4 py-3 text-slate-200">{s.username}</td>
                  <td className="px-4 py-3">
                    <Link
                      href={`/problems/${s.problem_slug}`}
                      className="text-emerald-300 transition hover:underline"
                    >
                      {s.problem_title || s.problem_slug}
                    </Link>
                    {s.contest != null && contestId == null && (
                      <span className="ml-2 text-xs text-slate-500">
                        contest #{s.contest}
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <VerdictBadge status={s.status} />
                  </td>
                  <td className="px-4 py-3 text-slate-400">
                    {new Date(s.submitted_at).toLocaleString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
