"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";

import { VerdictBadge } from "@/components/SubmissionStatus";
import { apiFetch } from "@/lib/api";
import type { Paginated, Submission } from "@/lib/types";

const IN_FLIGHT = new Set(["Pending", "Judging"]);

export function mySubmissionsKey(problemId: number) {
  return ["my-submissions", problemId] as const;
}

/** The student's own recent submissions to one problem, practice and contest. */
export function MySubmissions({ problemId }: { problemId: number }) {
  const { data, isLoading, error } = useQuery({
    queryKey: mySubmissionsKey(problemId),
    queryFn: () =>
      apiFetch<Paginated<Submission>>(`/submissions/?problem=${problemId}&user=me&page_size=10`),
    // Keep rows current while any of them is still being judged.
    refetchInterval: (query) =>
      query.state.data?.results.some((s) => IN_FLIGHT.has(s.status)) ? 3000 : false,
  });

  if (isLoading) return null;
  if (error) {
    return <p className="text-xs text-red-300">Couldn&apos;t load your submissions.</p>;
  }
  const rows = data?.results ?? [];

  return (
    <div className="space-y-2">
      <div className="flex items-baseline justify-between">
        <h3 className="font-medium text-white">My submissions</h3>
        {data && data.count > rows.length && (
          <Link href="/submissions" className="text-xs text-emerald-300 hover:underline">
            All {data.count} →
          </Link>
        )}
      </div>
      {rows.length === 0 ? (
        <p className="text-sm text-slate-500">No submissions to this problem yet.</p>
      ) : (
        <ul className="divide-y divide-slate-800 rounded-lg border border-slate-800 text-sm">
          {rows.map((s) => (
            <li key={s.id} className="flex items-center justify-between gap-3 px-3 py-2">
              <Link href={`/submissions/${s.id}`} className="text-emerald-300 hover:underline">
                #{s.id}
              </Link>
              <span className="flex-1 text-xs text-slate-500">
                {new Date(s.submitted_at).toLocaleString()}
                {s.contest ? " · contest" : " · practice"}
              </span>
              <VerdictBadge status={s.status} />
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
