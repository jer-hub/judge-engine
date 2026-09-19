"use client";

import { pageRange } from "@/lib/pagination";

type Props = {
  page: number;
  pageSize: number;
  count: number;
  onPageChange: (page: number) => void;
};

export function Pagination({ page, pageSize, count, onPageChange }: Props) {
  const { from, to, totalPages } = pageRange(count, page, pageSize);
  if (count === 0) return null;

  return (
    <div className="flex flex-wrap items-center justify-between gap-3 text-sm text-slate-400">
      <p>
        Showing{" "}
        <span className="tabular-nums text-slate-200">
          {from}–{to}
        </span>{" "}
        of <span className="tabular-nums text-slate-200">{count}</span>
      </p>
      <div className="flex items-center gap-2">
        <button
          type="button"
          disabled={page <= 1}
          onClick={() => onPageChange(page - 1)}
          className="cursor-pointer rounded border border-slate-700 px-3 py-1.5 transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-40"
        >
          Previous
        </button>
        <span className="tabular-nums text-slate-300">
          {page} / {Math.max(totalPages, 1)}
        </span>
        <button
          type="button"
          disabled={page >= totalPages}
          onClick={() => onPageChange(page + 1)}
          className="cursor-pointer rounded border border-slate-700 px-3 py-1.5 transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-40"
        >
          Next
        </button>
      </div>
    </div>
  );
}
