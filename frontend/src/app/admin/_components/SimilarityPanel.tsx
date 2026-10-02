"use client";

import Link from "next/link";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { formatApiErrorPayload } from "@/lib/admin";
import { ApiError, apiFetch } from "@/lib/api";
import type { Submission } from "@/lib/types";

type Side = { username: string; submission_id: number; status: string };
type Pair = { problem_letter: string; score: number; a: Side; b: Side };

function SourcePane({ side }: { side: Side }) {
  const { data, isLoading } = useQuery({
    queryKey: ["submission", side.submission_id],
    queryFn: () => apiFetch<Submission>(`/submissions/${side.submission_id}/`),
  });
  return (
    <div className="min-w-0 flex-1">
      <p className="mb-1 text-xs text-slate-400">
        <Link href={`/submissions/${side.submission_id}`} className="text-emerald-300 hover:underline">
          {side.username} · #{side.submission_id}
        </Link>{" "}
        ({side.status})
      </p>
      <pre className="max-h-96 overflow-auto rounded bg-slate-950 p-2 text-xs text-slate-200">
        {isLoading ? "Loading…" : (data?.source_code ?? "")}
      </pre>
    </div>
  );
}

/** Admin: pairs of students whose code for a problem is suspiciously alike.
 *  Computed on demand: it compares every pair of students per problem. */
export function SimilarityPanel({ contestId }: { contestId: number }) {
  const [threshold, setThreshold] = useState(0.6);
  const [requested, setRequested] = useState(false);
  const [open, setOpen] = useState<string | null>(null);

  const { data, isFetching, error, refetch } = useQuery({
    queryKey: ["admin", "similarity", contestId, threshold],
    queryFn: () =>
      apiFetch<{ pairs: Pair[] }>(`/contests/${contestId}/similarity/?threshold=${threshold}`),
    enabled: requested,
  });

  const pairs = data?.pairs ?? [];

  return (
    <div className="space-y-3 rounded border border-slate-800 bg-slate-900/40 p-3 text-sm">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-slate-400">Similar code</span>
        <select
          aria-label="Similarity threshold"
          value={threshold}
          onChange={(e) => setThreshold(Number(e.target.value))}
          className="rounded border border-slate-700 bg-slate-900 px-2 py-1 text-xs"
        >
          <option value={0.5}>50%+</option>
          <option value={0.6}>60%+</option>
          <option value={0.8}>80%+</option>
          <option value={0.9}>90%+</option>
        </select>
        <button
          type="button"
          onClick={() => (requested ? void refetch() : setRequested(true))}
          disabled={isFetching}
          className="cursor-pointer rounded border border-slate-700 px-3 py-1 text-xs text-emerald-300 hover:bg-slate-800 disabled:opacity-50"
        >
          {isFetching ? "Checking…" : "Check submissions"}
        </button>
        <span className="text-xs text-slate-500">
          A lead to review, not proof: short solutions to easy problems look alike.
        </span>
      </div>
      {error && (
        <p className="text-xs text-red-300">
          {error instanceof ApiError ? formatApiErrorPayload(error.payload, error.message) : String(error)}
        </p>
      )}
      {data && pairs.length === 0 && (
        <p className="text-xs text-slate-500">No pairs at or above {Math.round(threshold * 100)}%.</p>
      )}
      {pairs.length > 0 && (
        <ul className="space-y-2">
          {pairs.map((p) => {
            const key = `${p.a.submission_id}-${p.b.submission_id}`;
            return (
              <li key={key} className="rounded border border-slate-800 p-2">
                <div className="flex flex-wrap items-center gap-3 text-xs">
                  <span className="font-mono text-emerald-300">{p.problem_letter}</span>
                  <span className="text-slate-200">
                    {p.a.username} ↔ {p.b.username}
                  </span>
                  <span className={p.score >= 0.9 ? "text-red-300" : "text-amber-300"}>
                    {Math.round(p.score * 100)}% similar
                  </span>
                  <button
                    type="button"
                    onClick={() => setOpen(open === key ? null : key)}
                    className="cursor-pointer text-emerald-300 hover:underline"
                  >
                    {open === key ? "Hide" : "Compare"}
                  </button>
                </div>
                {open === key && (
                  <div className="mt-2 flex flex-col gap-2 lg:flex-row">
                    <SourcePane side={p.a} />
                    <SourcePane side={p.b} />
                  </div>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
