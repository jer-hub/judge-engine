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
    refetchInterval: 3000,
  });

  if (isLoading) return <p className="text-slate-400">Loading scoreboard…</p>;
  if (error || !data) {
    return <p className="text-red-300">{(error as Error)?.message || "Error"}</p>;
  }

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-3xl font-semibold text-white">{data.title}</h1>
          <p className="text-sm text-slate-400">ICPC-style scoreboard · auto-refresh 3s</p>
        </div>
        {data.is_frozen && (
          <span className="rounded bg-amber-900/50 px-3 py-1 text-sm text-amber-200">
            Scoreboard frozen
          </span>
        )}
      </div>

      <div className="overflow-x-auto rounded-xl border border-slate-800">
        <table className="w-full min-w-[640px] text-left text-sm">
          <thead className="bg-slate-900 text-slate-400">
            <tr>
              <th className="px-3 py-2">Rank</th>
              <th className="px-3 py-2">Team</th>
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
    </div>
  );
}
