"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";

import { VerdictBadge } from "@/components/SubmissionStatus";
import { apiFetch } from "@/lib/api";
import type { Paginated, Submission } from "@/lib/types";

export function SubmissionsPanel() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["admin", "submissions"],
    queryFn: () => apiFetch<Paginated<Submission>>("/submissions/"),
    refetchInterval: 8000,
  });

  return (
    <div className="space-y-4">
      <p className="text-sm text-slate-400">
        Platform-wide queue. Auto-refreshes every few seconds while this tab is open.
      </p>
      {isLoading && <p className="text-sm text-slate-400">Loading submissions…</p>}
      {error && <p className="text-sm text-red-300">{(error as Error).message}</p>}

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
              <tr key={s.id} className="border-t border-slate-800 hover:bg-slate-900/40">
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
                  {s.contest != null && (
                    <span className="ml-2 text-xs text-slate-500">contest #{s.contest}</span>
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
            {!isLoading && (data?.results?.length ?? 0) === 0 && (
              <tr>
                <td colSpan={5} className="px-4 py-8 text-center text-slate-500">
                  No submissions yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
