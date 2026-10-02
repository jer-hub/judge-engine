"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { ApiError, apiFetch } from "@/lib/api";
import type { Clarification } from "@/lib/types";

const POLL_MS = 15_000;

export function clarificationsKey(contestId: number | string) {
  return ["clarifications", String(contestId)] as const;
}

/** Shared by the contest page, the problem banner and the admin panel. */
export function useClarifications(contestId: number | string, enabled = true) {
  return useQuery({
    queryKey: clarificationsKey(contestId),
    queryFn: () => apiFetch<Clarification[]>(`/contests/${contestId}/clarifications/`),
    enabled,
    refetchInterval: POLL_MS,
  });
}

export function ClarificationItem({
  item,
  children,
}: {
  item: Clarification;
  /** Extra controls inside the item (the admin's answer form). */
  children?: React.ReactNode;
}) {
  return (
    <li
      className={`rounded-lg border p-3 text-sm ${
        item.is_announcement ? "border-sky-900/70 bg-sky-950/30" : "border-slate-800 bg-slate-900/40"
      }`}
    >
      <div className="mb-1 flex flex-wrap items-center gap-2 text-xs text-slate-500">
        {item.is_announcement ? (
          <span className="font-semibold text-sky-300">Announcement</span>
        ) : (
          <span>{item.mine ? "Your question" : "Question"}</span>
        )}
        {item.problem_letter && <span className="font-mono text-emerald-300">{item.problem_letter}</span>}
        {item.author && <span>by {item.author}</span>}
        <span>{new Date(item.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</span>
        {!item.is_announcement && item.mine && item.answered_at && !item.is_public && (
          <span>· answered privately</span>
        )}
      </div>
      {!item.is_announcement && <p className="whitespace-pre-wrap text-slate-200">{item.question}</p>}
      {item.answered_at ? (
        <p className={`whitespace-pre-wrap ${item.is_announcement ? "text-slate-100" : "mt-2 text-emerald-200"}`}>
          {!item.is_announcement && <span className="mr-1 text-xs text-slate-500">Answer:</span>}
          {item.answer}
        </p>
      ) : (
        <p className="mt-2 text-xs text-amber-300">Waiting for an answer…</p>
      )}
      {children}
    </li>
  );
}

type Props = {
  contestId: number;
  problemLetters: string[];
  /** Asking is open only while the contest runs for this student. */
  canAsk: boolean;
};

/** Student view: announcements, published answers, and their own questions. */
export function ContestClarifications({ contestId, problemLetters, canAsk }: Props) {
  const queryClient = useQueryClient();
  const { data, error } = useClarifications(contestId);
  const [question, setQuestion] = useState("");
  const [letter, setLetter] = useState("");

  const ask = useMutation({
    mutationFn: () =>
      apiFetch<Clarification>(`/contests/${contestId}/clarifications/`, {
        method: "POST",
        body: JSON.stringify({ question, problem_letter: letter || null }),
      }),
    onSuccess: () => {
      setQuestion("");
      void queryClient.invalidateQueries({ queryKey: clarificationsKey(contestId) });
    },
  });

  const items = data ?? [];

  return (
    <section className="space-y-3">
      <h2 className="text-lg font-medium text-white">Clarifications</h2>
      {canAsk && (
        <div className="space-y-2 rounded-lg border border-slate-800 p-3">
          <textarea
            aria-label="Your question"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            maxLength={2000}
            rows={2}
            placeholder="Ask your teacher about a problem statement…"
            className="w-full rounded border border-slate-700 bg-slate-950 px-3 py-2 text-sm"
          />
          <div className="flex flex-wrap items-center gap-2 text-sm">
            <select
              aria-label="About problem"
              value={letter}
              onChange={(e) => setLetter(e.target.value)}
              className="rounded border border-slate-700 bg-slate-900 px-2 py-1"
            >
              <option value="">General</option>
              {problemLetters.map((l) => (
                <option key={l} value={l}>
                  Problem {l}
                </option>
              ))}
            </select>
            <button
              type="button"
              onClick={() => ask.mutate()}
              disabled={!question.trim() || ask.isPending}
              className="cursor-pointer rounded bg-emerald-600 px-3 py-1 font-medium hover:bg-emerald-500 disabled:opacity-50"
            >
              {ask.isPending ? "Sending…" : "Ask"}
            </button>
            <span className="text-xs text-slate-500">
              Only your teacher sees it, unless they publish the answer for everyone.
            </span>
          </div>
          {ask.isError && (
            <p className="text-xs text-red-300">
              {ask.error instanceof ApiError ? ask.error.message : "Could not send your question."}
            </p>
          )}
        </div>
      )}
      {error && <p className="text-xs text-red-300">Couldn&apos;t load clarifications.</p>}
      {items.length === 0 ? (
        <p className="text-sm text-slate-500">No announcements or answers yet.</p>
      ) : (
        <ul className="space-y-2">
          {items.map((item) => (
            <ClarificationItem key={item.id} item={item} />
          ))}
        </ul>
      )}
    </section>
  );
}
