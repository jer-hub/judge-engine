"use client";

import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { EmptyState } from "@/components/EmptyState";
import { Pagination } from "@/components/Pagination";
import { useDebouncedValue } from "@/hooks/useDebouncedValue";
import { apiFetch } from "@/lib/api";
import { buildListQuery } from "@/lib/pagination";
import type { AuditEvent, Paginated } from "@/lib/types";

const PAGE_SIZE = 50;

const AREAS = [
  { value: "", label: "Everything" },
  { value: "problem.", label: "Problems" },
  { value: "test_case.", label: "Test cases" },
  { value: "contest.", label: "Contests" },
  { value: "submission.", label: "Submissions / rejudges" },
  { value: "user.", label: "Accounts" },
];

/** The audit trail: which admin changed what, and when (newest first). */
export function ActivityPanel() {
  const [area, setArea] = useState("");
  const [actor, setActor] = useState("");
  const debouncedActor = useDebouncedValue(actor.trim());
  const [page, setPage] = useState(1);

  useEffect(() => {
    setPage(1);
  }, [area, debouncedActor]);

  const { data, isLoading, error } = useQuery({
    queryKey: ["admin", "audit", area, debouncedActor, page],
    queryFn: () =>
      apiFetch<Paginated<AuditEvent>>(
        buildListQuery("/audit/", {
          action: area || undefined,
          actor: debouncedActor || undefined,
          page,
          page_size: PAGE_SIZE,
        }),
      ),
  });

  const rows = data?.results ?? [];

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-2 text-sm">
        <select
          aria-label="Area"
          value={area}
          onChange={(e) => setArea(e.target.value)}
          className="rounded-sm border border-slate-700 bg-slate-900 px-3 py-2"
        >
          {AREAS.map((a) => (
            <option key={a.value} value={a.value}>
              {a.label}
            </option>
          ))}
        </select>
        <input
          aria-label="Admin username"
          placeholder="Admin username"
          value={actor}
          onChange={(e) => setActor(e.target.value)}
          className="rounded-sm border border-slate-700 bg-slate-900 px-3 py-2"
        />
      </div>
      {isLoading && <p className="text-sm text-slate-400">Loading activity…</p>}
      {error && <p className="text-sm text-red-300">{(error as Error).message}</p>}
      {data && rows.length === 0 && (
        <EmptyState title="No activity" body="Admin changes made through this app appear here." />
      )}
      {rows.length > 0 && (
        <div className="overflow-x-auto rounded-xl border border-slate-800">
          <table className="w-full min-w-[640px] text-left text-sm">
            <thead className="bg-slate-900/80 text-slate-400">
              <tr>
                <th className="px-4 py-3">When</th>
                <th className="px-4 py-3">Admin</th>
                <th className="px-4 py-3">Action</th>
                <th className="px-4 py-3">Target</th>
                <th className="px-4 py-3">Fields</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((e) => (
                <tr key={e.id} className="border-t border-slate-800">
                  <td className="whitespace-nowrap px-4 py-2 text-slate-400">
                    {new Date(e.created_at).toLocaleString()}
                  </td>
                  <td className="px-4 py-2 text-white">{e.actor_username}</td>
                  <td className="px-4 py-2 font-mono text-xs text-emerald-300">{e.action}</td>
                  <td className="px-4 py-2 text-slate-300">{e.target}</td>
                  <td className="px-4 py-2 text-xs text-slate-500">{e.fields.join(", ") || "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {data && data.count > PAGE_SIZE && (
        <Pagination page={page} pageSize={PAGE_SIZE} count={data.count} onPageChange={setPage} />
      )}
    </div>
  );
}
