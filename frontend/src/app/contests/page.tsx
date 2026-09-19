"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";

import { apiFetch } from "@/lib/api";
import type { ContestListItem, Paginated } from "@/lib/types";

export default function ContestsPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["contests"],
    queryFn: () => apiFetch<Paginated<ContestListItem>>("/contests/"),
  });

  return (
    <div>
      <h1 className="mb-2 text-3xl font-semibold text-white">Contests</h1>
      <p className="mb-6 text-sm text-slate-400">Upcoming, live, and past contests.</p>
      {isLoading && <p className="text-slate-400">Loading…</p>}
      {error && <p className="text-red-300">{(error as Error).message}</p>}
      <div className="grid gap-3">
        {data?.results.map((c) => (
          <Link
            key={c.id}
            href={`/contests/${c.id}`}
            className="rounded-xl border border-slate-800 bg-slate-900/40 p-4 hover:border-emerald-700"
          >
            <div className="flex items-center justify-between gap-3">
              <h2 className="text-lg font-medium text-white">{c.title}</h2>
              <span className="rounded bg-slate-800 px-2 py-1 text-xs uppercase text-slate-300">
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
    </div>
  );
}
