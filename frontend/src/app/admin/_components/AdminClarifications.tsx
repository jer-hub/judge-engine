"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";

import { ClarificationItem, clarificationsKey, useClarifications } from "@/components/ContestClarifications";
import { formatApiErrorPayload } from "@/lib/admin";
import { ApiError, apiFetch } from "@/lib/api";
import type { Clarification } from "@/lib/types";

function errorText(err: Error) {
  return err instanceof ApiError ? formatApiErrorPayload(err.payload, err.message) : err.message;
}

function AnswerForm({ contestId, item }: { contestId: number; item: Clarification }) {
  const queryClient = useQueryClient();
  const [text, setText] = useState(item.answer);
  const [isPublic, setIsPublic] = useState(item.is_public);
  const save = useMutation({
    mutationFn: () =>
      apiFetch<Clarification>(`/contests/${contestId}/clarifications/${item.id}/answer/`, {
        method: "POST",
        body: JSON.stringify({ answer: text, is_public: isPublic }),
      }),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: clarificationsKey(contestId) }),
  });
  return (
    <div className="mt-2 space-y-2">
      <textarea
        aria-label="Answer"
        value={text}
        onChange={(e) => setText(e.target.value)}
        rows={2}
        maxLength={2000}
        className="w-full rounded border border-slate-700 bg-slate-950 px-3 py-2 text-sm"
      />
      <div className="flex flex-wrap items-center gap-3 text-xs">
        <label className="flex items-center gap-1.5">
          <input type="checkbox" checked={isPublic} onChange={(e) => setIsPublic(e.target.checked)} />
          Show question and answer to every contestant
        </label>
        <button
          type="button"
          onClick={() => save.mutate()}
          disabled={!text.trim() || save.isPending}
          className="cursor-pointer rounded border border-slate-700 px-3 py-1 text-emerald-300 hover:bg-slate-800 disabled:opacity-50"
        >
          {item.answered_at ? "Update answer" : "Answer"}
        </button>
        {save.isError && <span className="text-red-300">{errorText(save.error)}</span>}
      </div>
    </div>
  );
}

/** Admin: post announcements and answer questions (unanswered first). */
export function AdminClarifications({ contestId }: { contestId: number }) {
  const queryClient = useQueryClient();
  const { data } = useClarifications(contestId);
  const [announcement, setAnnouncement] = useState("");
  const post = useMutation({
    mutationFn: () =>
      apiFetch<Clarification>(`/contests/${contestId}/clarifications/`, {
        method: "POST",
        body: JSON.stringify({ answer: announcement }),
      }),
    onSuccess: () => {
      setAnnouncement("");
      void queryClient.invalidateQueries({ queryKey: clarificationsKey(contestId) });
    },
  });

  const items = [...(data ?? [])].sort(
    (a, b) => Number(!!a.answered_at) - Number(!!b.answered_at),
  );
  const waiting = items.filter((c) => !c.answered_at).length;

  return (
    <div className="space-y-3 rounded border border-slate-800 bg-slate-900/40 p-3 text-sm">
      <p className="text-slate-400">
        Clarifications{" "}
        {waiting > 0 && (
          <span className="rounded bg-amber-900/50 px-2 py-0.5 text-xs text-amber-200">
            {waiting} waiting
          </span>
        )}
      </p>
      <div className="flex flex-wrap items-start gap-2">
        <textarea
          aria-label="Announcement"
          value={announcement}
          onChange={(e) => setAnnouncement(e.target.value)}
          rows={2}
          maxLength={2000}
          placeholder="Announcement to every contestant…"
          className="min-w-[16rem] flex-1 rounded border border-slate-700 bg-slate-950 px-3 py-2 text-sm"
        />
        <button
          type="button"
          onClick={() => post.mutate()}
          disabled={!announcement.trim() || post.isPending}
          className="cursor-pointer rounded border border-slate-700 px-3 py-1 text-xs text-sky-300 hover:bg-slate-800 disabled:opacity-50"
        >
          Announce
        </button>
      </div>
      {post.isError && <p className="text-xs text-red-300">{errorText(post.error)}</p>}
      {items.length > 0 && (
        <ul className="space-y-2">
          {items.map((item) => (
            <ClarificationItem key={item.id} item={item}>
              {!item.is_announcement && <AnswerForm contestId={contestId} item={item} />}
            </ClarificationItem>
          ))}
        </ul>
      )}
    </div>
  );
}
