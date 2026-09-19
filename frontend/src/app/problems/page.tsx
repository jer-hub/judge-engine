"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { EmptyState } from "@/components/EmptyState";
import { Pagination } from "@/components/Pagination";
import { useDebouncedValue } from "@/hooks/useDebouncedValue";
import { apiFetch } from "@/lib/api";
import { buildListQuery } from "@/lib/pagination";
import type { Paginated, ProblemListItem } from "@/lib/types";

const PAGE_SIZE = 20;

export default function ProblemsPage() {
  const [difficulty, setDifficulty] = useState("");
  const [tag, setTag] = useState("");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const debouncedSearch = useDebouncedValue(search, 300);
  const debouncedTag = useDebouncedValue(tag, 300);

  useEffect(() => {
    setPage(1);
  }, [difficulty, debouncedTag, debouncedSearch]);

  const queryPath = buildListQuery("/problems/", {
    page,
    page_size: PAGE_SIZE,
    difficulty: difficulty || undefined,
    tag: debouncedTag.trim() || undefined,
    search: debouncedSearch.trim() || undefined,
  });

  const { data, isLoading, error, isFetching } = useQuery({
    queryKey: ["problems", difficulty, debouncedTag, debouncedSearch, page],
    queryFn: () => apiFetch<Paginated<ProblemListItem>>(queryPath),
    placeholderData: keepPreviousData,
  });

  const hasFilters = Boolean(difficulty || debouncedTag.trim() || debouncedSearch.trim());
  const rows = data?.results ?? [];

  function clearFilters() {
    setDifficulty("");
    setTag("");
    setSearch("");
    setPage(1);
  }

  return (
    <div>
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-semibold text-white">Problems</h1>
          <p className="text-sm text-slate-400">Practice set — Java solutions only for now.</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <input
            className="rounded border border-slate-700 bg-slate-900 px-3 py-2 text-sm"
            placeholder="Search"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            aria-label="Search problems"
          />
          <select
            className="rounded border border-slate-700 bg-slate-900 px-3 py-2 text-sm"
            value={difficulty}
            onChange={(e) => setDifficulty(e.target.value)}
          >
            <option value="">All difficulties</option>
            <option value="easy">Easy</option>
            <option value="medium">Medium</option>
            <option value="hard">Hard</option>
          </select>
          <input
            className="rounded border border-slate-700 bg-slate-900 px-3 py-2 text-sm"
            placeholder="Tag (e.g. math or math,dp)"
            value={tag}
            onChange={(e) => setTag(e.target.value)}
          />
        </div>
      </div>

      {isLoading && <p className="text-slate-400">Loading…</p>}
      {error && (
        <p className="text-red-300">{(error as Error).message}. Try signing in.</p>
      )}

      {!isLoading && !error && rows.length === 0 && (
        <EmptyState
          title={hasFilters ? "No problems match these filters" : "No problems published yet"}
          body={
            hasFilters
              ? "Clear filters or try a different tag/search."
              : "Ask your teacher to publish practice problems."
          }
          actionLabel={hasFilters ? "Clear filters" : undefined}
          onAction={hasFilters ? clearFilters : undefined}
        />
      )}

      {rows.length > 0 && (
        <div className="space-y-4">
          <div
            className={`overflow-x-auto rounded-xl border border-slate-800 ${isFetching ? "opacity-80" : ""}`}
          >
            <table className="w-full min-w-[560px] text-left text-sm">
              <thead className="bg-slate-900 text-slate-400">
                <tr>
                  <th className="px-4 py-3">Title</th>
                  <th className="px-4 py-3">Difficulty</th>
                  <th className="px-4 py-3">Limits</th>
                  <th className="px-4 py-3">Tags</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((p) => (
                  <tr key={p.id} className="border-t border-slate-800 hover:bg-slate-900/40">
                    <td className="px-4 py-3">
                      <Link
                        href={`/problems/${p.slug}`}
                        className="text-emerald-300 hover:underline"
                      >
                        {p.title}
                      </Link>
                    </td>
                    <td className="px-4 py-3 capitalize">{p.difficulty}</td>
                    <td className="px-4 py-3 text-slate-400">
                      {p.time_limit_ms} ms / {p.memory_limit_mb} MB
                    </td>
                    <td className="px-4 py-3 text-slate-400">
                      {p.tags.join(", ") || "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <Pagination
            page={page}
            pageSize={PAGE_SIZE}
            count={data?.count ?? 0}
            onPageChange={setPage}
          />
        </div>
      )}
    </div>
  );
}
