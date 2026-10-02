"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { ContestClarifications } from "@/components/ContestClarifications";
import { Countdown } from "@/components/Countdown";
import { apiFetch } from "@/lib/api";
import type { ContestDetail } from "@/lib/types";

export default function ContestDetailPage() {
  const params = useParams<{ id: string }>();
  const id = params.id;
  const qc = useQueryClient();

  const { data, isLoading, error } = useQuery({
    queryKey: ["contest", id],
    queryFn: () => apiFetch<ContestDetail>(`/contests/${id}/`),
  });

  const register = useMutation({
    mutationFn: () =>
      apiFetch(`/contests/${id}/register/`, { method: "POST", body: "{}" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["contest", id] }),
  });

  const refetchContest = useCallback(() => {
    void qc.invalidateQueries({ queryKey: ["contest", id] });
  }, [qc, id]);

  if (isLoading) return <p className="text-slate-400">Loading…</p>;
  if (error || !data) {
    return <p className="text-red-300">{(error as Error)?.message || "Not found"}</p>;
  }

  // my_status/my_end_time include this student's time extension, if any.
  const canSubmit = data.my_status === "active" && data.is_registered;
  const extraMinutes = Math.round(
    (new Date(data.my_end_time).getTime() - new Date(data.end_time).getTime()) / 60000,
  );

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-3xl font-semibold text-white">{data.title}</h1>
          <p className="mt-2 max-w-2xl text-sm text-slate-400">{data.description}</p>
        </div>
        <Countdown
          startTime={data.start_time}
          endTime={data.my_end_time}
          serverTime={data.server_time}
          // Start reveals the problems and enables links; end disables them.
          onPhaseChange={refetchContest}
        />
      </div>

      <div className="flex flex-wrap gap-3">
        {!data.is_registered && data.status !== "past" && (
          <button
            type="button"
            onClick={() => register.mutate()}
            disabled={register.isPending}
            className="rounded bg-emerald-600 px-4 py-2 text-sm font-medium hover:bg-emerald-500"
          >
            Register
          </button>
        )}
        {data.is_registered && (
          <span className="rounded bg-slate-800 px-3 py-2 text-sm text-emerald-300">
            Registered
          </span>
        )}
        {extraMinutes > 0 && (
          <span className="rounded bg-sky-950/60 px-3 py-2 text-sm text-sky-200">
            You have {extraMinutes} extra minute{extraMinutes === 1 ? "" : "s"}
          </span>
        )}
        <Link
          href={`/contests/${id}/scoreboard`}
          className="rounded border border-slate-700 px-4 py-2 text-sm hover:bg-slate-900"
        >
          Scoreboard
        </Link>
      </div>

      <div className="overflow-hidden rounded-xl border border-slate-800">
        <table className="w-full text-left text-sm">
          <thead className="bg-slate-900 text-slate-400">
            <tr>
              <th className="px-4 py-3">#</th>
              <th className="px-4 py-3">Problem</th>
              <th className="px-4 py-3">Points</th>
            </tr>
          </thead>
          <tbody>
            {data.problems.length === 0 && data.status === "upcoming" && (
              <tr className="border-t border-slate-800">
                <td colSpan={3} className="px-4 py-6 text-center text-slate-400">
                  Problems are revealed when the contest starts.
                </td>
              </tr>
            )}
            {data.problems.length === 0 && data.status !== "upcoming" && (
              <tr className="border-t border-slate-800">
                <td colSpan={3} className="px-4 py-6 text-center text-slate-400">
                  This contest has no problems.
                </td>
              </tr>
            )}
            {data.problems.map((cp) => (
              <tr key={cp.id} className="border-t border-slate-800">
                <td className="px-4 py-3 font-mono text-emerald-300">{cp.letter}</td>
                <td className="px-4 py-3">
                  {canSubmit ? (
                    <Link
                      href={`/problems/${cp.problem.slug}?contest=${data.id}`}
                      className="text-emerald-300 hover:underline"
                    >
                      {cp.problem.title}
                    </Link>
                  ) : data.my_status === "past" && data.practice_after_end ? (
                    <Link
                      href={`/problems/${cp.problem.slug}`}
                      className="text-emerald-300 hover:underline"
                    >
                      {cp.problem.title}{" "}
                      <span className="text-xs text-slate-500">(practice)</span>
                    </Link>
                  ) : (
                    <span>{cp.problem.title}</span>
                  )}
                </td>
                <td className="px-4 py-3">{cp.points}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {data.my_status !== "upcoming" && (
        <ContestClarifications
          contestId={data.id}
          problemLetters={data.problems.map((p) => p.letter)}
          canAsk={canSubmit}
        />
      )}
    </div>
  );
}
