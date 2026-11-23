"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { EmptyState } from "@/components/EmptyState";
import { Pagination } from "@/components/Pagination";
import { VerdictBadge } from "@/components/SubmissionStatus";
import { apiFetch } from "@/lib/api";
import { problemHref } from "@/lib/contest-context";
import { buildListQuery } from "@/lib/pagination";
import type { Paginated, Submission } from "@/lib/types";

const PAGE_SIZE = 20;

const VERDICT_OPTIONS = [
  { value: "", label: "All verdicts" },
  { value: "Accepted", label: "Accepted" },
  { value: "WrongAnswer", label: "Wrong Answer" },
  { value: "TimeLimitExceeded", label: "Time Limit Exceeded" },
  { value: "MemoryLimitExceeded", label: "Memory Limit Exceeded" },
  { value: "RuntimeError", label: "Runtime Error" },
  { value: "CompileError", label: "Compile Error" },
  { value: "Pending", label: "Pending" },
  { value: "Judging", label: "Judging" },
];

export default function SubmissionsPage() {
  const [statusFilter, setStatusFilter] = useState("");
  const [page, setPage] = useState(1);

  useEffect(() => {
    setPage(1);
  }, [statusFilter]);

  const queryPath = buildListQuery("/submissions/", {
    user: "me",
    page,
    page_size: PAGE_SIZE,
    status: statusFilter || undefined,
  });

  const { data, isLoading, error, isFetching } = useQuery({
    queryKey: ["submissions", "me", statusFilter, page],
    queryFn: () => apiFetch<Paginated<Submission>>(queryPath),
    placeholderData: keepPreviousData,
  });

  const hasFilters = Boolean(statusFilter);
  const rows = data?.results ?? [];

  function clearFilters() {
    setStatusFilter("");
    setPage(1);
  }

  return (
    <div>
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-semibold text-white">My submissions</h1>
          <p className="text-sm text-slate-400">
            Your attempts across practice and contests.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <select
            aria-label="Filter submissions by verdict"
            className="rounded-sm border border-slate-700 bg-slate-900 px-3 py-2 text-sm"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            {VERDICT_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      {isLoading && <p className="text-slate-400">Loading…</p>}
      {error && (
        <p role="alert" className="text-red-300">
          {(error as Error).message}
        </p>
      )}

      {!isLoading && !error && rows.length === 0 && (
        <EmptyState
          title={hasFilters ? "No submissions match this verdict" : "No submissions yet"}
          body={
            hasFilters
              ? "Clear the verdict filter to view all of your attempts."
              : "Open a problem or join a live contest to submit your first Java solution."
          }
          actionLabel={hasFilters ? "Clear filter" : undefined}
          onAction={hasFilters ? clearFilters : undefined}
        />
      )}

      {rows.length > 0 && (
        <div className="space-y-4">
          <div
            className={`overflow-x-auto rounded-xl border border-slate-800 ${isFetching ? "opacity-80" : ""}`}
          >
            <table className="w-full min-w-[560px] text-left text-sm">
              <thead className="bg-slate-900 text-slate-400">
                <tr>
                  <th className="px-4 py-3">ID</th>
                  <th className="px-4 py-3">Problem</th>
                  <th className="px-4 py-3">Mode</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">When</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((s) => (
                  <tr key={s.id} className="border-t border-slate-800 hover:bg-slate-900/40">
                    <td className="px-4 py-3 font-mono">
                      <Link
                        href={`/submissions/${s.id}`}
                        className="text-emerald-300 hover:underline"
                      >
                        #{s.id}
                      </Link>
                    </td>
                    <td className="px-4 py-3">
                      <Link
                        href={problemHref(s.problem_slug, s.contest)}
                        className="text-emerald-300 hover:underline"
                      >
                        {s.problem_title || s.problem_slug}
                      </Link>
                    </td>
                    <td className="px-4 py-3 text-xs text-slate-400">
                      {s.contest != null ? (
                        <Link
                          href={`/contests/${s.contest}`}
                          className="rounded-sm bg-emerald-950/60 px-2 py-0.5 text-emerald-300 hover:underline"
                        >
                          Contest #{s.contest}
                        </Link>
                      ) : (
                        <span className="text-slate-500">Practice</span>
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
          <Pagination
            page={page}
            pageSize={PAGE_SIZE}
            count={data?.count ?? 0}
            onPageChange={setPage}
          />
        </div>
      )}
    </div>
  );
}
