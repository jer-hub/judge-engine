"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";

import { formatApiErrorPayload } from "@/lib/admin";
import { ApiError, apiFetch } from "@/lib/api";
import type { ContestDetail } from "@/lib/types";

type Props = {
  contest: ContestDetail;
};

type ExtensionResult = { username: string; extra_minutes: number; ends_at: string };

function errorText(err: Error) {
  return err instanceof ApiError ? formatApiErrorPayload(err.payload, err.message) : err.message;
}

/**
 * Scoreboard reveal and per-student time extensions. Both act immediately
 * (their own endpoints), independent of the contest form's Save.
 */
export function ContestResultsControls({ contest }: Props) {
  const queryClient = useQueryClient();
  const [username, setUsername] = useState("");
  const [minutes, setMinutes] = useState(15);
  const [message, setMessage] = useState<{ ok: boolean; text: string } | null>(null);

  const participants = contest.participants ?? [];
  const extended = participants.filter((p) => p.extra_minutes > 0);

  function refresh() {
    void queryClient.invalidateQueries({ queryKey: ["admin", "contest", contest.id] });
    void queryClient.invalidateQueries({ queryKey: ["scoreboard", String(contest.id)] });
  }

  const reveal = useMutation({
    mutationFn: (revealed: boolean) =>
      apiFetch<ContestDetail>(`/contests/${contest.id}/reveal/`, {
        method: "POST",
        body: JSON.stringify({ revealed }),
      }),
    onSuccess: (data) => {
      queryClient.setQueryData(["admin", "contest", contest.id], data);
      refresh();
      setMessage({
        ok: true,
        text: data.is_frozen ? "Scoreboard frozen again." : "Final standings revealed to students.",
      });
    },
    onError: (err: Error) => setMessage({ ok: false, text: errorText(err) }),
  });

  const extend = useMutation({
    mutationFn: (body: { username: string; extra_minutes: number }) =>
      apiFetch<ExtensionResult>(`/contests/${contest.id}/extensions/`, {
        method: "POST",
        body: JSON.stringify(body),
      }),
    onSuccess: (data) => {
      refresh();
      setMessage({
        ok: true,
        text: data.extra_minutes
          ? `${data.username} can submit until ${new Date(data.ends_at).toLocaleString()}.`
          : `Removed ${data.username}'s extension.`,
      });
    },
    onError: (err: Error) => setMessage({ ok: false, text: errorText(err) }),
  });

  function addExtension() {
    if (!username) return;
    extend.mutate({ username, extra_minutes: minutes });
  }

  const revealedAt = contest.results_revealed_at ? new Date(contest.results_revealed_at) : null;

  return (
    <div className="space-y-3 rounded border border-slate-800 bg-slate-900/40 p-3 text-sm">
      <div className="flex flex-wrap items-center gap-3">
        <span className="text-slate-400">Scoreboard</span>
        <span
          className={`rounded px-2 py-0.5 text-xs ${
            contest.is_frozen ? "bg-amber-900/50 text-amber-200" : "bg-slate-800 text-slate-300"
          }`}
        >
          {contest.is_frozen
            ? "Frozen for students"
            : revealedAt
              ? "Revealed"
              : contest.status === "past"
                ? "Final"
                : "Live"}
        </span>
        {contest.is_frozen ? (
          <button
            type="button"
            onClick={() => reveal.mutate(true)}
            disabled={reveal.isPending}
            className="cursor-pointer rounded border border-slate-700 px-3 py-1 text-xs text-emerald-300 transition hover:bg-slate-800 disabled:opacity-50"
          >
            Reveal final standings
          </button>
        ) : (
          revealedAt && (
            <button
              type="button"
              onClick={() => reveal.mutate(false)}
              disabled={reveal.isPending}
              className="cursor-pointer rounded border border-slate-700 px-3 py-1 text-xs text-slate-300 transition hover:bg-slate-800 disabled:opacity-50"
            >
              Freeze again
            </button>
          )
        )}
      </div>

      <div className="space-y-2">
        <p className="text-slate-400">
          Time extensions{" "}
          <span className="text-xs text-slate-500">
            (extra minutes past the end for one student; applies immediately)
          </span>
        </p>
        <div className="flex flex-wrap items-center gap-2">
          <select
            aria-label="Student to extend"
            className="rounded border border-slate-700 bg-slate-900 px-2 py-1 text-xs"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
          >
            <option value="">Choose a registered student…</option>
            {participants.map((p) => (
              <option key={p.id} value={p.username}>
                {p.username}
              </option>
            ))}
          </select>
          <input
            type="number"
            min={0}
            max={1440}
            aria-label="Extra minutes"
            className="w-20 rounded border border-slate-700 bg-slate-900 px-2 py-1 text-xs"
            value={minutes}
            onChange={(e) => setMinutes(Math.max(0, Math.floor(Number(e.target.value) || 0)))}
            onKeyDown={(e) => {
              // This sits inside the contest form: Enter must not save it.
              if (e.key === "Enter") {
                e.preventDefault();
                addExtension();
              }
            }}
          />
          <span className="text-xs text-slate-500">min</span>
          <button
            type="button"
            onClick={addExtension}
            disabled={!username || extend.isPending}
            className="cursor-pointer rounded border border-slate-700 px-3 py-1 text-xs text-emerald-300 transition hover:bg-slate-800 disabled:opacity-50"
          >
            Set extension
          </button>
        </div>
        {participants.length === 0 && (
          <p className="text-xs text-slate-500">Save participants first to extend their time.</p>
        )}
        {extended.length > 0 && (
          <ul className="flex flex-wrap gap-1.5">
            {extended.map((p) => (
              <li
                key={p.id}
                className="flex items-center gap-1 rounded bg-slate-800 px-2 py-0.5 text-xs text-slate-200"
              >
                {p.username} +{p.extra_minutes} min
                <button
                  type="button"
                  aria-label={`Remove ${p.username}'s extension`}
                  onClick={() => extend.mutate({ username: p.username, extra_minutes: 0 })}
                  className="cursor-pointer px-1 text-slate-400 hover:text-red-300"
                >
                  ×
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

      {message && (
        <p role="status" className={`text-xs ${message.ok ? "text-emerald-300" : "text-red-300"}`}>
          {message.text}
        </p>
      )}
    </div>
  );
}
