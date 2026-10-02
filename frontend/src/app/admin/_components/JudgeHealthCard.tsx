"use client";

import { useQuery } from "@tanstack/react-query";

import { apiFetch } from "@/lib/api";
import type { JudgeHealth } from "@/lib/types";

function formatAge(seconds: number) {
  if (seconds < 90) return `${seconds}s`;
  if (seconds < 5400) return `${Math.round(seconds / 60)} min`;
  return `${Math.round(seconds / 3600)} h`;
}

function Dot({ ok }: { ok: boolean }) {
  return (
    <span
      aria-hidden="true"
      className={`inline-block h-2 w-2 rounded-full ${ok ? "bg-emerald-400" : "bg-red-400"}`}
    />
  );
}

/** Is judging working right now? Workers, queue depth, stuck submissions. */
export function JudgeHealthCard() {
  const { data, error } = useQuery({
    queryKey: ["admin", "judge-health"],
    queryFn: () => apiFetch<JudgeHealth>("/judge/health/"),
    refetchInterval: 15_000,
  });

  if (error) {
    return <p className="text-sm text-red-300">Judge health unavailable: {(error as Error).message}</p>;
  }
  if (!data) return null;

  const { submissions: s } = data;
  // A Pending submission waiting minutes means judging is not keeping up.
  const slow = (s.oldest_pending_seconds ?? 0) > 120;
  const problems = [
    !data.judge_worker_up && "The judge worker is not responding: submissions will wait.",
    !data.preview_worker_up && "The preview worker is not responding: Run will not work.",
    slow && `The oldest pending submission has waited ${formatAge(s.oldest_pending_seconds!)}.`,
    s.system_error > 0 && `${s.system_error} submission(s) in System Error (retried automatically).`,
  ].filter(Boolean) as string[];

  return (
    <div
      className={`rounded-xl border p-4 text-sm ${
        problems.length ? "border-amber-800/70 bg-amber-950/20" : "border-slate-800 bg-slate-950/50"
      }`}
    >
      <div className="flex flex-wrap items-center gap-x-6 gap-y-2">
        <span className="font-medium text-white">Judge</span>
        <span className="flex items-center gap-1.5 text-slate-300">
          <Dot ok={data.judge_worker_up} /> judge worker
        </span>
        <span className="flex items-center gap-1.5 text-slate-300">
          <Dot ok={data.preview_worker_up} /> preview worker
        </span>
        <span className="text-slate-400">
          queued {data.queues.judge ?? "?"} · judging {s.judging} · pending {s.pending}
          {s.oldest_pending_seconds != null && ` (oldest ${formatAge(s.oldest_pending_seconds)})`}
        </span>
      </div>
      {problems.length > 0 && (
        <ul className="mt-2 list-disc space-y-0.5 pl-5 text-xs text-amber-200">
          {problems.map((p) => (
            <li key={p}>{p}</li>
          ))}
        </ul>
      )}
    </div>
  );
}
