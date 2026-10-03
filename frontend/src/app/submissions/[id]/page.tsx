"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { ConfirmDialog } from "@/components/ConfirmDialog";
import { VerdictBadge, verdictLabel } from "@/components/SubmissionStatus";
import { ApiError, apiFetch } from "@/lib/api";
import type { Submission, User } from "@/lib/types";

export default function SubmissionDetailPage() {
  const params = useParams<{ id: string }>();
  const id = Number(params.id);
  const queryClient = useQueryClient();

  const me = useQuery({
    queryKey: ["me"],
    queryFn: () => apiFetch<User>("/auth/me/"),
    retry: false,
  });

  const { data, isLoading, error } = useQuery({
    queryKey: ["submission", id],
    queryFn: () => apiFetch<Submission>(`/submissions/${id}/`),
    enabled: Number.isFinite(id),
    refetchInterval: (q) => {
      const status = q.state.data?.status;
      return status && ["Pending", "Judging"].includes(status) ? 1500 : false;
    },
  });

  const [confirmForce, setConfirmForce] = useState(false);

  const rejudge = useMutation({
    mutationFn: (force: boolean = false) =>
      apiFetch<Submission>(
        `/submissions/${id}/rejudge/${force ? "?force=true" : ""}`,
        { method: "POST" },
      ),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["submission", id] });
      void queryClient.invalidateQueries({ queryKey: ["admin", "submissions"] });
      void queryClient.invalidateQueries({ queryKey: ["submissions"] });
    },
  });

  if (isLoading) return <p className="text-slate-400">Loading submission…</p>;
  if (error || !data) {
    return <p className="text-red-300">{(error as Error)?.message || "Not found"}</p>;
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-wide text-slate-500">
            Submission #{data.id}
          </p>
          <h1 className="mt-1 text-2xl font-semibold text-white">
            <Link
              href={`/problems/${data.problem_slug}`}
              className="text-emerald-300 hover:underline"
            >
              {data.problem_title || data.problem_slug}
            </Link>
          </h1>
          <p className="mt-1 text-sm text-slate-400">
            {data.username} · {data.language} ·{" "}
            {new Date(data.submitted_at).toLocaleString()}
            {data.contest != null ? ` · Contest #${data.contest}` : ""}
          </p>
        </div>
        <div className="flex items-center gap-3">
          <VerdictBadge status={data.status} />
          {me.data?.is_platform_admin && (
            <button
              type="button"
              disabled={rejudge.isPending}
              onClick={() => rejudge.mutate(false)}
              className="cursor-pointer rounded-sm border border-slate-700 px-3 py-1.5 text-sm text-slate-200 hover:bg-slate-800 disabled:opacity-60"
            >
              {rejudge.isPending ? "Rejudging…" : "Rejudge"}
            </button>
          )}
        </div>
      </div>

      {rejudge.isError && (
        <div className="flex flex-wrap items-center gap-3 text-sm text-red-300">
          <p>{(rejudge.error as Error).message}</p>
          {/* 409 = already queued/judging; stuck after a worker crash → force. */}
          {rejudge.error instanceof ApiError && rejudge.error.status === 409 && (
            <button
              type="button"
              onClick={() => setConfirmForce(true)}
              className="cursor-pointer rounded-sm border border-red-800 px-3 py-1 text-red-200 hover:bg-red-950/50"
            >
              Force rejudge
            </button>
          )}
        </div>
      )}

      <ConfirmDialog
        open={confirmForce}
        title="Force rejudge?"
        body="Use this only if the submission is stuck (for example after a judge worker crashed). If it is still being judged, both runs will write results."
        confirmLabel="Force rejudge"
        danger
        onConfirm={() => {
          setConfirmForce(false);
          rejudge.mutate(true);
        }}
        onCancel={() => setConfirmForce(false)}
      />

      {data.compile_error && (
        <pre className="overflow-x-auto rounded-lg bg-red-950/40 p-4 text-xs text-red-200">
          {data.compile_error}
        </pre>
      )}

      {data.source_code != null && (
        <div>
          <h2 className="mb-2 text-sm font-medium text-slate-300">Source</h2>
          <pre className="max-h-[420px] overflow-auto rounded-lg border border-slate-800 bg-slate-950 p-4 font-mono text-xs text-slate-200">
            {data.source_code}
          </pre>
        </div>
      )}

      <div>
        <h2 className="mb-2 text-sm font-medium text-slate-300">Test results</h2>
        {(data.results?.length ?? 0) === 0 ? (
          <p className="text-sm text-slate-500">No results yet.</p>
        ) : (
          <div className="overflow-x-auto rounded-xl border border-slate-800">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-900 text-slate-400">
                <tr>
                  <th className="px-4 py-2">Test</th>
                  <th className="px-4 py-2">Verdict</th>
                  <th className="px-4 py-2">Time</th>
                </tr>
              </thead>
              <tbody>
                {data.results.map((r) => (
                  <tr key={r.id} className="border-t border-slate-800">
                    <td className="px-4 py-2">
                      #{r.test_case_order}
                      {r.is_sample ? " (sample)" : ""}
                    </td>
                    <td className="px-4 py-2">{verdictLabel(r.verdict)}</td>
                    <td className="px-4 py-2 text-slate-400">
                      {r.execution_time_ms != null ? `${r.execution_time_ms} ms` : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        <p className="mt-2 text-xs text-slate-500">
          Scoreboard uses ICPC binary scoring (solved / not). Running all tests only expands
          per-test feedback.
        </p>
      </div>
    </div>
  );
}
