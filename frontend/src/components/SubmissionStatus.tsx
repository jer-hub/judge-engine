"use client";

import { useQuery } from "@tanstack/react-query";

import { apiFetch } from "@/lib/api";
import type { Submission } from "@/lib/types";

const PENDING = new Set(["Pending", "Judging"]);
// The judge itself failed, not the student's code.
const SYSTEM_ERROR = "SystemError";

type Props = {
  submissionId: number | null;
};

export function SubmissionStatus({ submissionId }: Props) {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["submission", submissionId],
    queryFn: () => apiFetch<Submission>(`/submissions/${submissionId}/`),
    enabled: !!submissionId,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status && PENDING.has(status)) return 1500;
      // The server re-judges SystemError on its own; check back now and then.
      return status === SYSTEM_ERROR ? 15_000 : false;
    },
  });

  if (!submissionId) {
    return (
      <div className="rounded-lg border border-slate-800 bg-slate-900/50 p-4 text-sm text-slate-400">
        Submit a solution to see the verdict here.
      </div>
    );
  }

  if (!data && error && !isLoading) {
    // Without this the panel said "Judging…" forever: polling only starts
    // once a status is known.
    return (
      <div className="flex items-center justify-between gap-3 rounded-lg border border-red-900/60 bg-red-950/30 p-4 text-sm text-red-200">
        <span>Couldn&apos;t load the verdict: {(error as Error).message}</span>
        <button
          type="button"
          onClick={() => void refetch()}
          className="rounded border border-red-800 px-3 py-1 transition hover:bg-red-900/40"
        >
          Retry
        </button>
      </div>
    );
  }

  if (isLoading || !data) {
    return (
      <div className="rounded-lg border border-slate-800 bg-slate-900/50 p-4 text-sm">
        Judging…
      </div>
    );
  }

  return (
    <div className="space-y-3 rounded-lg border border-slate-800 bg-slate-900/50 p-4">
      <div className="flex items-center justify-between">
        <h3 className="font-medium text-white">Submission #{data.id}</h3>
        <VerdictBadge status={data.status} />
      </div>
      {data.compile_error && (
        <pre className="overflow-x-auto rounded bg-red-950/40 p-3 text-xs text-red-200">
          {data.compile_error}
        </pre>
      )}
      {data.results?.length > 0 && (
        <table className="w-full text-left text-sm">
          <thead className="text-slate-400">
            <tr>
              <th className="py-1">Test</th>
              <th>Verdict</th>
              <th>Time</th>
            </tr>
          </thead>
          <tbody>
            {data.results.map((r) => (
              <tr key={r.id} className="border-t border-slate-800">
                <td className="py-1">
                  #{r.test_case_order}
                  {r.is_sample ? " (sample)" : ""}
                </td>
                <td>{verdictLabel(r.verdict)}</td>
                <td>{r.execution_time_ms != null ? `${r.execution_time_ms} ms` : "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

const LABELS: Record<string, string> = {
  WrongAnswer: "Wrong Answer",
  TimeLimitExceeded: "Time Limit Exceeded",
  MemoryLimitExceeded: "Memory Limit Exceeded",
  OutputLimitExceeded: "Output Limit Exceeded",
  RuntimeError: "Runtime Error",
  CompileError: "Compile Error",
  SystemError: "System Error",
  JudgeBusy: "Judge Busy",
};

export function verdictLabel(status: string) {
  return LABELS[status] ?? status;
}

export function VerdictBadge({ status }: { status: string }) {
  const color =
    status === "Accepted"
      ? "bg-emerald-900/60 text-emerald-300"
      : PENDING.has(status) || status === SYSTEM_ERROR
        ? "bg-amber-900/60 text-amber-200"
        : "bg-red-900/60 text-red-200";
  return (
    <span className={`rounded px-2 py-1 text-xs font-semibold ${color}`}>
      {verdictLabel(status)}
    </span>
  );
}
