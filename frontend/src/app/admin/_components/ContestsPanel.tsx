"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { formatApiErrorPayload } from "@/lib/admin";
import { ApiError, apiFetch } from "@/lib/api";
import type { ContestListItem, Paginated } from "@/lib/types";

import { ContestEditor } from "./ContestEditor";

type CreateContestBody = {
  title: string;
  description: string;
  start_time: string;
  end_time: string;
  is_public: boolean;
  freeze_scoreboard_minutes_before_end: number;
};

function toLocalInputValue(date: Date) {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

function defaultWindow() {
  const start = new Date();
  start.setMinutes(start.getMinutes() + 30);
  const end = new Date(start);
  end.setHours(end.getHours() + 2);
  return {
    start_time: toLocalInputValue(start),
    end_time: toLocalInputValue(end),
  };
}

function statusTone(status: ContestListItem["status"]) {
  if (status === "active") return "bg-emerald-900/50 text-emerald-300";
  if (status === "upcoming") return "bg-sky-900/50 text-sky-200";
  return "bg-slate-800 text-slate-400";
}

export function ContestsPanel() {
  const queryClient = useQueryClient();
  const windowDefaults = defaultWindow();
  const [formOpen, setFormOpen] = useState(false);
  const [editId, setEditId] = useState<number | null>(null);
  const [form, setForm] = useState<CreateContestBody>({
    title: "",
    description: "",
    start_time: windowDefaults.start_time,
    end_time: windowDefaults.end_time,
    is_public: true,
    freeze_scoreboard_minutes_before_end: 0,
  });
  const [formError, setFormError] = useState<string | null>(null);

  const { data, isLoading, error } = useQuery({
    queryKey: ["admin", "contests"],
    queryFn: () => apiFetch<Paginated<ContestListItem>>("/contests/"),
  });

  const createMutation = useMutation({
    mutationFn: (body: CreateContestBody) =>
      apiFetch<ContestListItem>("/contests/", {
        method: "POST",
        body: JSON.stringify({
          ...body,
          start_time: new Date(body.start_time).toISOString(),
          end_time: new Date(body.end_time).toISOString(),
        }),
      }),
    onSuccess: (created) => {
      setFormOpen(false);
      setFormError(null);
      const next = defaultWindow();
      setForm({
        title: "",
        description: "",
        start_time: next.start_time,
        end_time: next.end_time,
        is_public: true,
        freeze_scoreboard_minutes_before_end: 0,
      });
      void queryClient.invalidateQueries({ queryKey: ["admin", "contests"] });
      void queryClient.invalidateQueries({ queryKey: ["contests"] });
      setEditId(created.id);
    },
    onError: (err: Error) => {
      if (err instanceof ApiError) {
        setFormError(formatApiErrorPayload(err.payload, err.message));
      } else {
        setFormError(err.message);
      }
    },
  });

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    setFormError(null);
    if (!form.title.trim()) {
      setFormError("Title is required.");
      return;
    }
    const start = new Date(form.start_time);
    const end = new Date(form.end_time);
    if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime())) {
      setFormError("Start and end times must be valid.");
      return;
    }
    if (end <= start) {
      setFormError("End time must be after start time.");
      return;
    }
    createMutation.mutate(form);
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-slate-400">
          Create a contest, then attach problems and invite participants.
        </p>
        <button
          type="button"
          onClick={() => setFormOpen((v) => !v)}
          className="cursor-pointer rounded-lg bg-emerald-500 px-3 py-2 text-sm font-medium text-slate-950 transition hover:bg-emerald-400"
        >
          {formOpen ? "Close form" : "New contest"}
        </button>
      </div>

      {formOpen && (
        <form
          onSubmit={onSubmit}
          className="grid gap-3 rounded-xl border border-slate-800 bg-slate-950/50 p-4 sm:grid-cols-2"
        >
          <label className="block text-sm sm:col-span-2">
            <span className="mb-1 block text-slate-400">Title</span>
            <input
              className="w-full rounded border border-slate-700 bg-slate-900 px-3 py-2"
              value={form.title}
              onChange={(e) => setForm((prev) => ({ ...prev, title: e.target.value }))}
              required
            />
          </label>
          <label className="block text-sm sm:col-span-2">
            <span className="mb-1 block text-slate-400">Description</span>
            <textarea
              className="min-h-[80px] w-full rounded border border-slate-700 bg-slate-900 px-3 py-2 text-sm"
              value={form.description}
              onChange={(e) =>
                setForm((prev) => ({ ...prev, description: e.target.value }))
              }
            />
          </label>
          <label className="block text-sm">
            <span className="mb-1 block text-slate-400">Start</span>
            <input
              type="datetime-local"
              className="w-full rounded border border-slate-700 bg-slate-900 px-3 py-2"
              value={form.start_time}
              onChange={(e) =>
                setForm((prev) => ({ ...prev, start_time: e.target.value }))
              }
              required
            />
          </label>
          <label className="block text-sm">
            <span className="mb-1 block text-slate-400">End</span>
            <input
              type="datetime-local"
              className="w-full rounded border border-slate-700 bg-slate-900 px-3 py-2"
              value={form.end_time}
              onChange={(e) => setForm((prev) => ({ ...prev, end_time: e.target.value }))}
              required
            />
          </label>
          <label className="block text-sm">
            <span className="mb-1 block text-slate-400">Freeze (minutes before end)</span>
            <input
              type="number"
              min={0}
              className="w-full rounded border border-slate-700 bg-slate-900 px-3 py-2"
              value={form.freeze_scoreboard_minutes_before_end}
              onChange={(e) =>
                setForm((prev) => ({
                  ...prev,
                  freeze_scoreboard_minutes_before_end: Number(e.target.value),
                }))
              }
            />
          </label>
          <label className="flex items-center gap-2 self-end text-sm">
            <input
              type="checkbox"
              checked={form.is_public}
              onChange={(e) =>
                setForm((prev) => ({ ...prev, is_public: e.target.checked }))
              }
              className="cursor-pointer"
            />
            <span>Public contest</span>
          </label>
          {formError && <p className="text-sm text-red-300 sm:col-span-2">{formError}</p>}
          <div className="sm:col-span-2">
            <button
              type="submit"
              disabled={createMutation.isPending}
              className="cursor-pointer rounded-lg bg-emerald-500 px-4 py-2 text-sm font-medium text-slate-950 transition hover:bg-emerald-400 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {createMutation.isPending ? "Creating…" : "Create & configure"}
            </button>
          </div>
        </form>
      )}

      {isLoading && <p className="text-sm text-slate-400">Loading contests…</p>}
      {error && <p className="text-sm text-red-300">{(error as Error).message}</p>}

      <div className="overflow-x-auto rounded-xl border border-slate-800">
        <table className="w-full min-w-[640px] text-left text-sm">
          <thead className="bg-slate-900/80 text-slate-400">
            <tr>
              <th className="px-4 py-3 font-medium">Contest</th>
              <th className="px-4 py-3 font-medium">Window</th>
              <th className="px-4 py-3 font-medium">Status</th>
              <th className="px-4 py-3 font-medium">Problems</th>
              <th className="px-4 py-3 font-medium">Actions</th>
            </tr>
          </thead>
          <tbody>
            {(data?.results ?? []).map((c) => (
              <tr key={c.id} className="border-t border-slate-800 hover:bg-slate-900/40">
                <td className="px-4 py-3">
                  <Link
                    href={`/contests/${c.id}`}
                    className="font-medium text-emerald-300 transition hover:underline"
                  >
                    {c.title}
                  </Link>
                </td>
                <td className="px-4 py-3 text-xs text-slate-400">
                  {new Date(c.start_time).toLocaleString()}
                  <br />→ {new Date(c.end_time).toLocaleString()}
                </td>
                <td className="px-4 py-3">
                  <span
                    className={`rounded px-2 py-1 text-xs font-semibold uppercase ${statusTone(c.status)}`}
                  >
                    {c.status}
                  </span>
                </td>
                <td className="px-4 py-3 text-slate-400">{c.problem_count ?? "—"}</td>
                <td className="px-4 py-3 space-x-3 text-xs">
                  <button
                    type="button"
                    onClick={() => setEditId((id) => (id === c.id ? null : c.id))}
                    className="cursor-pointer text-emerald-300 hover:underline"
                  >
                    {editId === c.id ? "Close" : "Manage"}
                  </button>
                  <Link
                    href={`/contests/${c.id}/scoreboard`}
                    className="text-slate-300 transition hover:text-white"
                  >
                    Scoreboard
                  </Link>
                </td>
              </tr>
            ))}
            {!isLoading && (data?.results?.length ?? 0) === 0 && (
              <tr>
                <td colSpan={5} className="px-4 py-8 text-center text-slate-500">
                  No contests yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {editId != null && (
        <ContestEditor contestId={editId} onClose={() => setEditId(null)} />
      )}
    </div>
  );
}
