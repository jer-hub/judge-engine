"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { ConfirmDialog } from "@/components/ConfirmDialog";
import { EmptyState } from "@/components/EmptyState";
import { RichTextEditor } from "@/components/RichTextEditor";
import { Pagination } from "@/components/Pagination";
import { useDebouncedValue } from "@/hooks/useDebouncedValue";
import { djangoAdminUrl, formatApiErrorPayload } from "@/lib/admin";
import { ApiError, apiFetch } from "@/lib/api";
import { buildListQuery } from "@/lib/pagination";
import type { Paginated, ProblemListItem } from "@/lib/types";

import { MagnifyingGlassIcon } from "./icons";
import { ProblemEditForm } from "./ProblemEditForm";
import { TestCaseEditor } from "./TestCaseEditor";

type CreateProblemBody = {
  title: string;
  slug: string;
  statement: string;
  difficulty: string;
  tags: string;
  time_limit_ms: number;
  memory_limit_mb: number;
  is_published: boolean;
  run_all_tests: boolean;
};

type AdminProblem = ProblemListItem & {
  test_case_count?: number;
  run_all_tests?: boolean;
  created_by_username?: string | null;
};

const PAGE_SIZE = 20;

function slugify(title: string) {
  return title
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 80);
}

export function ProblemsPanel() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const debouncedSearch = useDebouncedValue(search, 300);
  const [page, setPage] = useState(1);
  const [formOpen, setFormOpen] = useState(false);
  const [editorProblem, setEditorProblem] = useState<AdminProblem | null>(null);
  const [editSlug, setEditSlug] = useState<string | null>(null);
  const [confirm, setConfirm] = useState<
    | { type: "publish"; problem: AdminProblem; next: boolean }
    | { type: "delete"; problem: AdminProblem }
    | null
  >(null);
  const [form, setForm] = useState<CreateProblemBody>({
    title: "",
    slug: "",
    statement: "",
    difficulty: "easy",
    tags: "",
    time_limit_ms: 2000,
    memory_limit_mb: 256,
    is_published: false,
    run_all_tests: false,
  });
  const [formError, setFormError] = useState<string | null>(null);

  useEffect(() => {
    setPage(1);
  }, [debouncedSearch]);

  const queryPath = buildListQuery("/problems/", {
    page,
    page_size: PAGE_SIZE,
    search: debouncedSearch.trim() || undefined,
  });

  const { data, isLoading, error, isFetching } = useQuery({
    queryKey: ["admin", "problems", "list", { page, search: debouncedSearch }],
    queryFn: () => apiFetch<Paginated<AdminProblem>>(queryPath),
    placeholderData: keepPreviousData,
  });

  const publishMutation = useMutation({
    mutationFn: ({ slug, is_published }: { slug: string; is_published: boolean }) =>
      apiFetch<AdminProblem>(`/problems/${slug}/`, {
        method: "PATCH",
        body: JSON.stringify({ is_published }),
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["admin", "problems"] });
      void queryClient.invalidateQueries({ queryKey: ["problems"] });
      setConfirm(null);
      setFormError(null);
    },
    onError: (err: Error) => {
      setFormError(
        err instanceof ApiError
          ? formatApiErrorPayload(err.payload, err.message)
          : err.message,
      );
      setConfirm(null);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (slug: string) =>
      apiFetch<null>(`/problems/${slug}/`, { method: "DELETE" }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ["admin", "problems"] });
      void queryClient.invalidateQueries({ queryKey: ["problems"] });
      setConfirm(null);
    },
    onError: (err: Error) => {
      setFormError(
        err instanceof ApiError
          ? formatApiErrorPayload(err.payload, err.message)
          : err.message,
      );
      setConfirm(null);
    },
  });

  const createMutation = useMutation({
    mutationFn: (body: CreateProblemBody) =>
      apiFetch<AdminProblem>("/problems/", {
        method: "POST",
        body: JSON.stringify(body),
      }),
    onSuccess: () => {
      setFormOpen(false);
      setFormError(null);
      setForm({
        title: "",
        slug: "",
        statement: "",
        difficulty: "easy",
        tags: "",
        time_limit_ms: 2000,
        memory_limit_mb: 256,
        is_published: false,
        run_all_tests: false,
      });
      void queryClient.invalidateQueries({ queryKey: ["admin", "problems"] });
      void queryClient.invalidateQueries({ queryKey: ["problems"] });
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
    const slug = form.slug || slugify(form.title);
    if (!form.title.trim() || !slug || !form.statement.trim()) {
      setFormError("Title, slug, and statement are required.");
      return;
    }
    createMutation.mutate({ ...form, slug });
  }

  const rows = data?.results ?? [];
  const hasFilters = Boolean(debouncedSearch.trim());

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="relative min-w-[220px] flex-1">
          <MagnifyingGlassIcon
            className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500"
            aria-hidden="true"
          />
          <input
            className="w-full rounded-lg border border-slate-700 bg-slate-950/70 py-2 pl-9 pr-3 text-sm text-slate-100 outline-none transition focus:border-emerald-600 focus:ring-1 focus:ring-emerald-600"
            placeholder="Search title, slug, or tag"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            aria-label="Search problems"
          />
        </div>
        <button
          type="button"
          onClick={() => setFormOpen((v) => !v)}
          className="cursor-pointer rounded-lg bg-emerald-500 px-3 py-2 text-sm font-medium text-slate-950 transition hover:bg-emerald-400"
        >
          {formOpen ? "Close form" : "New problem"}
        </button>
      </div>

      {formOpen && (
        <form
          onSubmit={onSubmit}
          className="grid gap-3 rounded-xl border border-slate-800 bg-slate-950/50 p-4 sm:grid-cols-2"
        >
          <label className="block text-sm">
            <span className="mb-1 block text-slate-400">Title</span>
            <input
              className="w-full rounded border border-slate-700 bg-slate-900 px-3 py-2"
              value={form.title}
              onChange={(e) => {
                const title = e.target.value;
                setForm((prev) => ({
                  ...prev,
                  title,
                  slug: prev.slug || slugify(title),
                }));
              }}
              required
            />
          </label>
          <label className="block text-sm">
            <span className="mb-1 block text-slate-400">
              Slug <span className="text-slate-500">(set at creation; cannot change later)</span>
            </span>
            <input
              className="w-full rounded border border-slate-700 bg-slate-900 px-3 py-2 font-mono text-xs"
              value={form.slug}
              onChange={(e) => setForm((prev) => ({ ...prev, slug: e.target.value }))}
              required
            />
          </label>
          <RichTextEditor
            id="problem-statement"
            value={form.statement}
            onChange={(statement) => setForm((prev) => ({ ...prev, statement }))}
            required
            minHeight={220}
          />
          <label className="block text-sm">
            <span className="mb-1 block text-slate-400">Difficulty</span>
            <select
              className="w-full rounded border border-slate-700 bg-slate-900 px-3 py-2"
              value={form.difficulty}
              onChange={(e) => setForm((prev) => ({ ...prev, difficulty: e.target.value }))}
            >
              <option value="easy">Easy</option>
              <option value="medium">Medium</option>
              <option value="hard">Hard</option>
            </select>
          </label>
          <label className="block text-sm">
            <span className="mb-1 block text-slate-400">Tags (comma-separated)</span>
            <input
              className="w-full rounded border border-slate-700 bg-slate-900 px-3 py-2"
              value={form.tags}
              onChange={(e) => setForm((prev) => ({ ...prev, tags: e.target.value }))}
            />
          </label>
          <label className="block text-sm">
            <span className="mb-1 block text-slate-400">Time limit (ms)</span>
            <input
              type="number"
              min={100}
              max={30000}
              className="w-full rounded border border-slate-700 bg-slate-900 px-3 py-2"
              value={form.time_limit_ms}
              onChange={(e) =>
                setForm((prev) => ({ ...prev, time_limit_ms: Number(e.target.value) }))
              }
            />
          </label>
          <label className="block text-sm">
            <span className="mb-1 block text-slate-400">Memory (MB, min 96)</span>
            <input
              type="number"
              min={96}
              max={2048}
              className="w-full rounded border border-slate-700 bg-slate-900 px-3 py-2"
              value={form.memory_limit_mb}
              onChange={(e) =>
                setForm((prev) => ({ ...prev, memory_limit_mb: Number(e.target.value) }))
              }
            />
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={form.run_all_tests}
              onChange={(e) =>
                setForm((prev) => ({ ...prev, run_all_tests: e.target.checked }))
              }
              className="cursor-pointer"
            />
            <span>Run all tests for full feedback (scoreboard stays ICPC binary)</span>
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={form.is_published}
              onChange={(e) =>
                setForm((prev) => ({ ...prev, is_published: e.target.checked }))
              }
              className="cursor-pointer"
            />
            <span>Publish immediately (needs test cases)</span>
          </label>
          {formError && <p className="text-sm text-red-300 sm:col-span-2">{formError}</p>}
          <div className="sm:col-span-2">
            <button
              type="submit"
              disabled={createMutation.isPending}
              className="cursor-pointer rounded-lg bg-emerald-500 px-4 py-2 text-sm font-medium text-slate-950 transition hover:bg-emerald-400 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {createMutation.isPending ? "Creating…" : "Create problem"}
            </button>
          </div>
        </form>
      )}

      {formError && !formOpen && <p className="text-sm text-red-300">{formError}</p>}
      {isLoading && <p className="text-sm text-slate-400">Loading problems…</p>}
      {error && <p className="text-sm text-red-300">{(error as Error).message}</p>}

      {!isLoading && rows.length === 0 && (
        <EmptyState
          title={hasFilters ? "No problems match these filters" : "No problems yet"}
          body={
            hasFilters
              ? "Try a different search term."
              : "Create a problem, then add test cases before publishing."
          }
          actionLabel={hasFilters ? "Clear search" : undefined}
          onAction={hasFilters ? () => setSearch("") : undefined}
        />
      )}

      {rows.length > 0 && (
        <>
          <div className={`overflow-x-auto rounded-xl border border-slate-800 ${isFetching ? "opacity-80" : ""}`}>
            <table className="w-full min-w-[720px] text-left text-sm">
              <thead className="bg-slate-900/80 text-slate-400">
                <tr>
                  <th className="px-4 py-3 font-medium">Problem</th>
                  <th className="px-4 py-3 font-medium">Difficulty</th>
                  <th className="px-4 py-3 font-medium">Tests</th>
                  <th className="px-4 py-3 font-medium">Published</th>
                  <th className="px-4 py-3 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((p) => (
                  <tr key={p.id} className="border-t border-slate-800 align-top hover:bg-slate-900/40">
                    <td className="px-4 py-3">
                      <Link
                        href={`/problems/${p.slug}`}
                        className="font-medium text-emerald-300 transition hover:underline"
                      >
                        {p.title}
                      </Link>
                      <p className="font-mono text-xs text-slate-500">{p.slug}</p>
                      {p.created_by_username && (
                        <p className="text-xs text-slate-600">by {p.created_by_username}</p>
                      )}
                    </td>
                    <td className="px-4 py-3 capitalize text-slate-300">{p.difficulty}</td>
                    <td className="px-4 py-3">
                      <button
                        type="button"
                        onClick={() =>
                          setEditorProblem((cur) => (cur?.id === p.id ? null : p))
                        }
                        className="cursor-pointer text-xs text-emerald-300 transition hover:underline"
                      >
                        Test cases ({p.test_case_count ?? 0})
                      </button>
                    </td>
                    <td className="px-4 py-3">
                      <button
                        type="button"
                        disabled={publishMutation.isPending}
                        onClick={() =>
                          setConfirm({
                            type: "publish",
                            problem: p,
                            next: !p.is_published,
                          })
                        }
                        className={`cursor-pointer rounded px-2 py-1 text-xs font-semibold transition ${
                          p.is_published
                            ? "bg-emerald-900/50 text-emerald-300 hover:bg-emerald-900/80"
                            : "bg-slate-800 text-slate-400 hover:bg-slate-700"
                        }`}
                        aria-pressed={p.is_published}
                        aria-label={`${p.is_published ? "Unpublish" : "Publish"} ${p.title}`}
                      >
                        {p.is_published ? "Live" : "Draft"}
                      </button>
                    </td>
                    <td className="px-4 py-3 space-x-3 text-xs">
                      <button
                        type="button"
                        onClick={() =>
                          setEditSlug((s) => (s === p.slug ? null : p.slug))
                        }
                        className="cursor-pointer text-emerald-300 hover:underline"
                      >
                        {editSlug === p.slug ? "Close edit" : "Edit"}
                      </button>
                      <a
                        href={djangoAdminUrl(`problems/problem/${p.id}/change/`)}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-slate-400 transition hover:text-white"
                      >
                        Django
                      </a>
                      <button
                        type="button"
                        onClick={() => setConfirm({ type: "delete", problem: p })}
                        className="cursor-pointer text-red-300 transition hover:text-red-200"
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {editorProblem && (
            <TestCaseEditor
              problemId={editorProblem.id}
              problemTitle={editorProblem.title}
              onClose={() => setEditorProblem(null)}
            />
          )}

          {editSlug && (
            <ProblemEditForm slug={editSlug} onClose={() => setEditSlug(null)} />
          )}

          <Pagination
            page={page}
            pageSize={PAGE_SIZE}
            count={data?.count ?? 0}
            onPageChange={setPage}
          />
        </>
      )}

      <ConfirmDialog
        open={confirm?.type === "publish"}
        title={confirm?.type === "publish" && confirm.next ? "Publish problem?" : "Unpublish problem?"}
        body={
          confirm?.type === "publish" && confirm.next
            ? `Publish “${confirm.problem.title}”? Students will see it immediately.`
            : `Unpublish “${confirm?.type === "publish" ? confirm.problem.title : ""}”? Students lose access.`
        }
        confirmLabel={confirm?.type === "publish" && confirm.next ? "Publish" : "Unpublish"}
        danger={confirm?.type === "publish" && !confirm.next}
        onCancel={() => setConfirm(null)}
        onConfirm={() => {
          if (confirm?.type !== "publish") return;
          publishMutation.mutate({
            slug: confirm.problem.slug,
            is_published: confirm.next,
          });
        }}
      />

      <ConfirmDialog
        open={confirm?.type === "delete"}
        title="Delete problem?"
        body={
          confirm?.type === "delete"
            ? `Permanently delete “${confirm.problem.title}”? If it has submissions, the API will refuse and you should unpublish instead.`
            : ""
        }
        confirmLabel="Delete"
        danger
        onCancel={() => setConfirm(null)}
        onConfirm={() => {
          if (confirm?.type !== "delete") return;
          deleteMutation.mutate(confirm.problem.slug);
        }}
      />
    </div>
  );
}
