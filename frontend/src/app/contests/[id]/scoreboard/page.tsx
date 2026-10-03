"use client";

import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";

import { apiFetch } from "@/lib/api";
import type { Scoreboard, User } from "@/lib/types";

export default function ScoreboardPage() {
  const params = useParams<{ id: string }>();
  const id = params.id;

  const { data: me } = useQuery({
    queryKey: ["me"],
    queryFn: () => apiFetch<User>("/auth/me/"),
    retry: false,
  });

  const { data, isLoading, error } = useQuery({
    queryKey: ["scoreboard", id],
    queryFn: () => apiFetch<Scoreboard>(`/contests/${id}/scoreboard/`),
    // After the contest, keep polling only until the last verdicts land.
    refetchInterval: (query) => {
      const board = query.state.data;
      const settled =
        board?.status === "past" &&
        board.standings.every((row) => row.problems.every((cell) => !cell.pending));
      return settled ? false : 3000;
    },
  });

  if (isLoading) return <p className="text-slate-400">Loading scoreboard…</p>;
  // Only a failed first load replaces the table; a failed refresh keeps the
  // last standings on screen (it may be projected for the whole class).
  if (!data) {
    return <p className="text-red-300">{(error as Error)?.message || "Error"}</p>;
  }

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-3xl font-semibold text-white">{data.title}</h1>
          <p className="text-sm text-slate-400">
            ICPC-style scoreboard ·{" "}
            {data.status === "past" ? "final standings" : "auto-refresh 3s"}
          </p>
          {error && (
            <p className="text-sm text-amber-300">Connection lost — showing the last standings, retrying…</p>
          )}
        </div>
        {data.freeze_at && !data.is_frozen && data.status === "active" && (
          <span className="rounded-sm bg-slate-800 px-3 py-1 text-sm text-slate-300">
            Freezes at {new Date(data.freeze_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
          </span>
        )}
        {data.is_frozen && data.freeze_at && data.status !== "past" && (
          <span className="rounded-sm bg-amber-900/50 px-3 py-1 text-sm text-amber-200">
            Frozen since{" "}
            {new Date(data.freeze_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
            : new results are hidden
          </span>
        )}
        {data.is_frozen && data.status === "past" && (
          <span className="rounded-sm bg-amber-900/50 px-3 py-1 text-sm text-amber-200">
            Results held: final standings will be revealed by your teacher
          </span>
        )}
      </div>

      <div className="overflow-x-auto rounded-xl border border-slate-800">
        <table className="w-full min-w-[640px] text-left text-sm">
          <thead className="bg-slate-900 text-slate-400">
            <tr>
              <th className="px-3 py-2">Rank</th>
              <th className="px-3 py-2">Student</th>
              <th className="px-3 py-2">Solved</th>
              <th className="px-3 py-2">Penalty</th>
              {data.problems.map((p) => (
                <th key={p.letter} className="px-3 py-2 text-center">
                  {p.letter}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.standings.map((row) => {
              const highlight = me && me.username === row.username;
              return (
                <tr
                  key={row.username}
                  className={
                    highlight
                      ? "border-t border-slate-800 bg-emerald-950/40"
                      : "border-t border-slate-800"
                  }
                >
                  <td className="px-3 py-2">{row.rank}</td>
                  <td className="px-3 py-2 font-medium">{row.username}</td>
                  <td className="px-3 py-2">{row.solved}</td>
                  <td className="px-3 py-2">{row.penalty}</td>
                  {row.problems.map((cell) => (
                    <td key={cell.letter} className="px-3 py-2 text-center font-mono text-xs">
                      {cell.solved ? (
                        <span className="text-emerald-300">
                          +{cell.attempts > 1 ? cell.attempts : ""}
                          {cell.solve_time_min != null ? ` (${cell.solve_time_min})` : ""}
                        </span>
                      ) : cell.pending ? (
                        <span className="text-amber-300">?</span>
                      ) : cell.attempts > 0 ? (
                        <span className="text-red-300">-{cell.attempts}</span>
                      ) : (
                        <span className="text-slate-600">.</span>
                      )}
                    </td>
                  ))}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <dl className="mt-4 flex flex-wrap gap-x-6 gap-y-2 text-xs text-slate-400">
        <div>
          <dt className="inline font-mono text-emerald-300">+2 (34)</dt>
          <dd className="inline"> solved on the 2nd try, at minute 34</dd>
        </div>
        <div>
          <dt className="inline font-mono text-red-300">-3</dt>
          <dd className="inline"> 3 wrong tries, not solved</dd>
        </div>
        <div>
          <dt className="inline font-mono text-amber-300">?</dt>
          <dd className="inline"> judging, or hidden by the freeze</dd>
        </div>
        <div>
          <dd className="inline">
            Penalty: minutes to each solve + 20 per wrong try before it. Compile errors are free.
          </dd>
        </div>
      </dl>
    </div>
  );
}
