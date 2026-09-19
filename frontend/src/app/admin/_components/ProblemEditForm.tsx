"use client";

import { FormEvent, useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { formatApiErrorPayload } from "@/lib/admin";
import { ApiError, apiFetch } from "@/lib/api";
import type { ProblemDetail } from "@/lib/types";

import { RichTextEditor } from "@/components/RichTextEditor";

type Props = {
  slug: string;
  onClose: () => void;
};

export function ProblemEditForm({ slug, onClose }: Props) {
  const queryClient = useQueryClient();
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState({
    title: "",
    statement: "",
    difficulty: "easy",
    tags: "",
    time_limit_ms: 2000,
    memory_limit_mb: 256,
    run_all_tests: false,
    is_published: false,
  });

  const detail = useQuery({
    queryKey: ["problem", slug],
    queryFn: () => apiFetch<ProblemDetail>(`/problems/${slug}/`),
  });

  useEffect(() => {
    if (!detail.data) return;
    const p = detail.data;
    setForm({
      title: p.title,
      statement: p.statement,
      difficulty: p.difficulty,
      tags: p.tags.join(", "),
      time_limit_ms: p.time_limit_ms,
      memory_limit_mb: p.memory_limit_mb,
      run_all_tests: p.run_all_tests,
      is_published: p.is_published,
    });
  }, [detail.data]);

  const save = useMutation({
    mutationFn: () =>
      apiFetch<ProblemDetail>(`/problems/${slug}/`, {
        method: "PATCH",
        body: JSON.stringify(form),
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["admin", "problems"] });
      void queryClient.invalidateQueries({ queryKey: ["problems"] });
      void queryClient.invalidateQueries({ queryKey: ["problem", slug] });
      onClose();
    },
    onError: (err: Error) => {
      setError(
        err instanceof ApiError
          ? formatApiErrorPayload(err.payload, err.message)
          : err.message,
      );
    },
  });

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    if (!form.title.trim() || !form.statement.trim()) {
      setError("Title and statement are required.");
      return;
    }
    save.mutate();
  }

  return (
    <form
      onSubmit={onSubmit}
      className="mt-3 grid gap-3 rounded-xl border border-slate-700 bg-slate-950/70 p-4 sm:grid-cols-2"
    >
      <div className="flex items-center justify-between sm:col-span-2">
        <h4 className="text-sm font-medium text-white">Edit {slug}</h4>
        <button
          type="button"
          onClick={onClose}
          className="cursor-pointer text-xs text-slate-400 hover:text-white"
        >
          Close
        </button>
      </div>
      {detail.isLoading && <p className="text-xs text-slate-500 sm:col-span-2">Loading…</p>}
      <label className="block text-sm sm:col-span-2">
        <span className="mb-1 block text-slate-400">Title</span>
        <input
          className="w-full rounded border border-slate-700 bg-slate-900 px-3 py-2"
          value={form.title}
          onChange={(e) => setForm((p) => ({ ...p, title: e.target.value }))}
          required
        />
      </label>
      <p className="text-xs text-slate-500 sm:col-span-2">
        Slug <span className="font-mono text-slate-400">{slug}</span> is permanent.
      </p>
      <RichTextEditor
        id="edit-problem-statement"
        value={form.statement}
        onChange={(statement) => setForm((p) => ({ ...p, statement }))}
        required
        minHeight={260}
      />
      <label className="block text-sm">
        <span className="mb-1 block text-slate-400">Difficulty</span>
        <select
          className="w-full rounded border border-slate-700 bg-slate-900 px-3 py-2"
          value={form.difficulty}
          onChange={(e) => setForm((p) => ({ ...p, difficulty: e.target.value }))}
        >
          <option value="easy">Easy</option>
          <option value="medium">Medium</option>
          <option value="hard">Hard</option>
        </select>
      </label>
      <label className="block text-sm">
        <span className="mb-1 block text-slate-400">Tags</span>
        <input
          className="w-full rounded border border-slate-700 bg-slate-900 px-3 py-2"
          value={form.tags}
          onChange={(e) => setForm((p) => ({ ...p, tags: e.target.value }))}
        />
      </label>
      <label className="block text-sm">
        <span className="mb-1 block text-slate-400">Time (ms)</span>
        <input
          type="number"
          min={100}
          max={30000}
          className="w-full rounded border border-slate-700 bg-slate-900 px-3 py-2"
          value={form.time_limit_ms}
          onChange={(e) =>
            setForm((p) => ({ ...p, time_limit_ms: Number(e.target.value) }))
          }
        />
      </label>
      <label className="block text-sm">
        <span className="mb-1 block text-slate-400">Memory (MB)</span>
        <input
          type="number"
          min={96}
          max={2048}
          className="w-full rounded border border-slate-700 bg-slate-900 px-3 py-2"
          value={form.memory_limit_mb}
          onChange={(e) =>
            setForm((p) => ({ ...p, memory_limit_mb: Number(e.target.value) }))
          }
        />
      </label>
      <label className="flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          checked={form.run_all_tests}
          onChange={(e) => setForm((p) => ({ ...p, run_all_tests: e.target.checked }))}
          className="cursor-pointer"
        />
        Run all tests (feedback only; ICPC scoreboard unchanged)
      </label>
      <label className="flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          checked={form.is_published}
          onChange={(e) => setForm((p) => ({ ...p, is_published: e.target.checked }))}
          className="cursor-pointer"
        />
        Published
      </label>
      {error && <p className="text-sm text-red-300 sm:col-span-2">{error}</p>}
      <div className="sm:col-span-2">
        <button
          type="submit"
          disabled={save.isPending}
          className="cursor-pointer rounded-lg bg-emerald-500 px-4 py-2 text-sm font-medium text-slate-950 hover:bg-emerald-400 disabled:opacity-60"
        >
          {save.isPending ? "Saving…" : "Save changes"}
        </button>
      </div>
    </form>
  );
}
