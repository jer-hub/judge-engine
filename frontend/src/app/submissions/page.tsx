"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";

import { VerdictBadge } from "@/components/SubmissionStatus";
import { apiFetch } from "@/lib/api";
import type { Paginated, Submission } from "@/lib/types";

export default function SubmissionsPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["submissions", "me"],
    queryFn: () => apiFetch<Paginated<Submission>>("/submissions/?user=me"),
  });

  return (
    <div>
      <h1 className="mb-2 text-3xl font-semibold text-white">My submissions</h1>
      <p className="mb-6 text-sm text-slate-400">Your recent attempts across practice and contests.</p>
      {isLoading && <p className="text-slate-400">Loading…</p>}
      {error && <p className="text-red-300">{(error as Error).message}</p>}
      <div className="overflow-hidden rounded-xl border border-slate-800">
        <table className="w-full text-left text-sm">
          <thead className="bg-slate-900 text-slate-400">
            <tr>
              <th className="px-4 py-3">ID</th>
              <th className="px-4 py-3">Problem</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3">When</th>
            </tr>
          </thead>
          <tbody>
            {data?.results.map((s) => (
              <tr key={s.id} className="border-t border-slate-800">
                <td className="px-4 py-3 font-mono">
                  <Link href={`/submissions/${s.id}`} className="text-emerald-300 hover:underline">
                    #{s.id}
                  </Link>
                </td>
                <td className="px-4 py-3">
                  <Link
                    href={`/problems/${s.problem_slug}`}
                    className="text-emerald-300 hover:underline"
                  >
                    {s.problem_title || s.problem_slug}
                  </Link>
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
    </div>
  );
}
