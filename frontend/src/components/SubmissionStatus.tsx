"use client";

import { useQuery } from "@tanstack/react-query";

import { apiFetch } from "@/lib/api";
import type { Submission } from "@/lib/types";

const PENDING = new Set(["Pending", "Judging"]);

type Props = {
  submissionId: number | null;
};

export function SubmissionStatus({ submissionId }: Props) {
  const { data, isLoading } = useQuery({
    queryKey: ["submission", submissionId],
    queryFn: () => apiFetch<Submission>(`/submissions/${submissionId}/`),
    enabled: !!submissionId,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status && PENDING.has(status) ? 1500 : false;
    },
  });

  if (!submissionId) {
    return (
      <div className="rounded-lg border border-slate-800 bg-slate-900/50 p-4 text-sm text-slate-400">
        Submit a solution to see the verdict here.
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
                <td>{r.verdict}</td>
                <td>{r.execution_time_ms != null ? `${r.execution_time_ms} ms` : "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

export function VerdictBadge({ status }: { status: string }) {
  const color =
    status === "Accepted"
      ? "bg-emerald-900/60 text-emerald-300"
      : PENDING.has(status)
        ? "bg-amber-900/60 text-amber-200"
        : "bg-red-900/60 text-red-200";
  return (
    <span className={`rounded px-2 py-1 text-xs font-semibold ${color}`}>
      {status}
    </span>
  );
}
