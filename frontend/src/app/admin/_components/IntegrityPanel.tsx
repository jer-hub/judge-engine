"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { formatApiErrorPayload } from "@/lib/admin";
import { ApiError, apiFetch } from "@/lib/api";

type RecentEvent = {
  type: string;
  count: number;
  meta: Record<string, unknown>;
  created_at: string;
};

type StudentRow = {
  user_id: number;
  username: string;
  visibility_hidden: number;
  window_blur: number;
  editor_paste: number;
  fullscreen_exit?: number;
  submit_ips: string[];
  shared_ip_with: string[];
  blocked?: boolean;
  ack_count?: number;
  recent_events: RecentEvent[];
};

type IntegritySummary = {
  contest_id: number;
  integrity_monitoring: boolean;
  integrity_strict?: boolean;
  students: StudentRow[];
  event_counts: number;
};

/** Admin: warn-only focus/paste/IP leads; unlock soft-blocked students. */
export function IntegrityPanel({ contestId }: { contestId: number }) {
  const queryClient = useQueryClient();
  const [openUser, setOpenUser] = useState<number | null>(null);
  const [unlockErrors, setUnlockErrors] = useState<Record<string, string>>({});

  const { data, isFetching, error, refetch, isFetched } = useQuery({
    queryKey: ["admin", "integrity", contestId],
    queryFn: () => apiFetch<IntegritySummary>(`/contests/${contestId}/integrity/`),
  });

  const unlock = useMutation({
    mutationFn: (username: string) =>
      apiFetch<{ username: string }>(`/contests/${contestId}/integrity-unlock/`, {
        method: "POST",
        body: JSON.stringify({ username }),
      }),
    onSuccess: (_data, username) => {
      setUnlockErrors((prev) => {
        if (!(username in prev)) return prev;
        const next = { ...prev };
        delete next[username];
        return next;
      });
      void refetch();
      void queryClient.invalidateQueries({ queryKey: ["admin", "contest", contestId] });
      void queryClient.invalidateQueries({ queryKey: ["contest", String(contestId)] });
      void queryClient.invalidateQueries({ queryKey: ["admin", "contests", "list"] });
      void queryClient.invalidateQueries({ queryKey: ["admin", "contests", "metrics"] });
    },
    onError: (err: Error, username) => {
      setUnlockErrors((prev) => ({
        ...prev,
        [username]:
          err instanceof ApiError
            ? formatApiErrorPayload(err.payload, err.message)
            : err.message,
      }));
    },
  });

  const students = data?.students ?? [];
  const flagged = students.filter(
    (s) =>
      !!s.blocked ||
      s.shared_ip_with.length > 0 ||
      s.visibility_hidden + s.window_blur >= 10 ||
      s.editor_paste >= 5,
  );

  return (
    <div className="space-y-3 rounded-sm border border-slate-800 bg-slate-900/40 p-3 text-sm">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-slate-400">Integrity signals</span>
        <button
          type="button"
          onClick={() => void refetch()}
          disabled={isFetching}
          className="cursor-pointer rounded-sm border border-slate-700 px-3 py-1 text-xs text-emerald-300 hover:bg-slate-800 disabled:opacity-50"
        >
          {isFetching ? "Refreshing…" : isFetched ? "Refresh" : "Load"}
        </button>
        <span className="text-xs text-slate-500">
          Leads for review, not proof of cheating. Clipboard text is never stored.
          Soft-blocked students wait for a teacher unlock here.
        </span>
      </div>

      {error && (
        <p className="text-xs text-red-300">
          {error instanceof ApiError
            ? formatApiErrorPayload(error.payload, error.message)
            : String(error)}
        </p>
      )}

      {data && !data.integrity_monitoring && (
        <p className="text-xs text-amber-300">
          Monitoring is off for this contest — clients are not sending signals.
        </p>
      )}

      {data?.integrity_strict && (
        <p className="text-xs text-emerald-300/90">
          Strict mode on: fullscreen required; Submit soft-blocks until you unlock the student.
        </p>
      )}

      {data && (
        <p className="text-xs text-slate-500">
          {data.event_counts} event row{data.event_counts === 1 ? "" : "s"} stored
          {flagged.length > 0 ? ` · ${flagged.length} student(s) with notable signals` : ""}
        </p>
      )}

      {students.length === 0 && data ? (
        <p className="text-xs text-slate-500">No participants yet.</p>
      ) : (
        <ul className="max-h-80 space-y-1 overflow-y-auto">
          {students.map((s) => {
            const notable =
              !!s.blocked ||
              s.shared_ip_with.length > 0 ||
              s.visibility_hidden + s.window_blur > 0 ||
              s.editor_paste > 0;
            if (!notable && students.length > 20) return null;
            const expanded = openUser === s.user_id;
            const rowError = unlockErrors[s.username];
            return (
              <li key={s.user_id} className="rounded border border-slate-800/80">
                <div className="flex flex-wrap items-center gap-2 px-2 py-1.5">
                  <button
                    type="button"
                    onClick={() => setOpenUser(expanded ? null : s.user_id)}
                    className="flex min-w-0 flex-1 cursor-pointer flex-wrap items-center gap-x-3 gap-y-1 text-left text-xs hover:opacity-90"
                  >
                    <span className="font-medium text-slate-200">{s.username}</span>
                    {s.blocked && (
                      <span className="rounded bg-red-950/80 px-1.5 py-0.5 text-red-200">
                        Blocked
                      </span>
                    )}
                    <span className="text-slate-500">
                      hide {s.visibility_hidden} · blur {s.window_blur} · paste {s.editor_paste}
                      {typeof s.fullscreen_exit === "number"
                        ? ` · fs-exit ${s.fullscreen_exit}`
                        : ""}
                      {typeof s.ack_count === "number" && s.ack_count > 0
                        ? ` · unlocks ${s.ack_count}`
                        : ""}
                    </span>
                    {s.submit_ips.length > 0 && (
                      <span className="font-mono text-slate-400">
                        {s.submit_ips.join(", ")}
                      </span>
                    )}
                    {s.shared_ip_with.length > 0 && (
                      <span className="rounded bg-amber-950/70 px-1.5 py-0.5 text-amber-200">
                        same IP as {s.shared_ip_with.join(", ")}
                      </span>
                    )}
                  </button>
                  {s.blocked && (
                    <button
                      type="button"
                      disabled={unlock.isPending && unlock.variables === s.username}
                      onClick={() => unlock.mutate(s.username)}
                      className="cursor-pointer rounded-sm border border-emerald-700 px-2 py-0.5 text-xs text-emerald-300 hover:bg-emerald-950/50 disabled:opacity-50"
                    >
                      Unlock
                    </button>
                  )}
                </div>
                {rowError && (
                  <p className="px-2 pb-1.5 text-xs text-red-300">{rowError}</p>
                )}
                {expanded && (
                  <ul className="border-t border-slate-800 px-2 py-1.5 text-xs text-slate-400">
                    {s.recent_events.length === 0 ? (
                      <li>No recent events.</li>
                    ) : (
                      s.recent_events.map((ev, i) => (
                        <li key={`${ev.created_at}-${i}`} className="py-0.5">
                          <span className="text-slate-300">{ev.type}</span>
                          {ev.count > 1 ? ` ×${ev.count}` : ""}
                          {typeof ev.meta?.chars === "number"
                            ? ` (~${ev.meta.chars} chars)`
                            : ""}
                          {typeof ev.meta?.unlocked_by === "string"
                            ? ` (by ${ev.meta.unlocked_by})`
                            : ""}
                          <span className="ml-2 text-slate-600">
                            {new Date(ev.created_at).toLocaleString()}
                          </span>
                        </li>
                      ))
                    )}
                  </ul>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
