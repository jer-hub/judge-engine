"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { EmptyState } from "@/components/EmptyState";
import { Pagination } from "@/components/Pagination";
import { useDebouncedValue } from "@/hooks/useDebouncedValue";
import { apiFetch } from "@/lib/api";
import { buildListQuery } from "@/lib/pagination";
import type { ContestListItem, Paginated } from "@/lib/types";

const PAGE_SIZE = 20;

export default function ContestsPage() {
  const [statusFilter, setStatusFilter] = useState("");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const debouncedSearch = useDebouncedValue(search, 300);

  useEffect(() => {
    setPage(1);
  }, [statusFilter, debouncedSearch]);

  const queryPath = buildListQuery("/contests/", {
    page,
    page_size: PAGE_SIZE,
    status: statusFilter || undefined,
    search: debouncedSearch.trim() || undefined,
  });

  const { data, isLoading, error, isFetching } = useQuery({
    queryKey: ["contests", statusFilter, debouncedSearch, page],
    queryFn: () => apiFetch<Paginated<ContestListItem>>(queryPath),
    placeholderData: keepPreviousData,
  });

  const hasFilters = Boolean(statusFilter || debouncedSearch.trim());
  const rows = data?.results ?? [];

  function clearFilters() {
    setStatusFilter("");
    setSearch("");
    setPage(1);
  }

  return (
    <div>
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-semibold text-white">Contests</h1>
          <p className="text-sm text-slate-400">Upcoming, live, and past contests.</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <input
            className="rounded-sm border border-slate-700 bg-slate-900 px-3 py-2 text-sm"
            placeholder="Search contests"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            aria-label="Search contests"
          />
          <select
            aria-label="Filter contests by status"
            className="rounded-sm border border-slate-700 bg-slate-900 px-3 py-2 text-sm"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            <option value="">All statuses</option>
            <option value="active">Active</option>
            <option value="upcoming">Upcoming</option>
            <option value="past">Past</option>
          </select>
        </div>
      </div>

      {isLoading && <p className="text-slate-400">Loading…</p>}
      {error && (
        <p role="alert" className="text-red-300">
          {(error as Error).message}
        </p>
      )}

      {!isLoading && !error && rows.length === 0 && (
        <EmptyState
          title={hasFilters ? "No contests match these filters" : "No contests scheduled yet"}
          body={
            hasFilters
              ? "Clear filters or try another search term."
              : "Check back when your teacher publishes an upcoming or live contest."
          }
          actionLabel={hasFilters ? "Clear filters" : undefined}
          onAction={hasFilters ? clearFilters : undefined}
        />
      )}

      {rows.length > 0 && (
        <div className="space-y-4">
          <div className={`grid gap-3 ${isFetching ? "opacity-80" : ""}`}>
            {rows.map((c) => (
              <Link
                key={c.id}
                href={`/contests/${c.id}`}
                className="rounded-xl border border-slate-800 bg-slate-900/40 p-4 transition hover:border-emerald-700"
              >
                <div className="flex items-center justify-between gap-3">
                  <h2 className="text-lg font-medium text-white">{c.title}</h2>
                  <span
                    className={`rounded-sm px-2 py-1 text-xs uppercase ${
                      c.status === "active"
                        ? "bg-emerald-950/70 text-emerald-300"
                        : c.status === "upcoming"
                          ? "bg-sky-950/70 text-sky-200"
                          : "bg-slate-800 text-slate-300"
                    }`}
                  >
                    {c.status}
                  </span>
                </div>
                <p className="mt-1 text-sm text-slate-400">
                  {new Date(c.start_time).toLocaleString()} →{" "}
                  {new Date(c.end_time).toLocaleString()}
                </p>
              </Link>
            ))}
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
