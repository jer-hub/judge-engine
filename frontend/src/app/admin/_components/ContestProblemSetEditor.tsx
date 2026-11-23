"use client";

import { useState } from "react";

import type { ContestProblemRow } from "@/lib/contest-editor";
import type { ProblemListItem } from "@/lib/types";

type Props = {
  problems: ContestProblemRow[];
  catalogProblems: ProblemListItem[];
  onAddProblem: (id: number) => void;
  onRemoveProblem: (idx: number) => void;
  onMoveProblem: (idx: number, dir: -1 | 1) => void;
  onAddAllPublished: () => void;
};

export function ContestProblemSetEditor({
  problems,
  catalogProblems,
  onAddProblem,
  onRemoveProblem,
  onMoveProblem,
  onAddAllPublished,
}: Props) {
  const [problemSearch, setProblemSearch] = useState("");

  const usedIds = new Set(problems.map((p) => p.problem_id));
  const available = catalogProblems.filter((p) => !usedIds.has(p.id));
  const filteredAvailable = available.filter((p) => {
    const q = problemSearch.trim().toLowerCase();
    if (!q) return true;
    return p.title.toLowerCase().includes(q) || p.slug.toLowerCase().includes(q);
  });

  return (
    <div>
      <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
        <h5 className="text-sm font-medium text-slate-200">
          Problem set{" "}
          <span className="font-normal text-slate-500">({problems.length})</span>
        </h5>
        <button
          type="button"
          onClick={onAddAllPublished}
          className="cursor-pointer text-xs text-emerald-300 hover:underline"
        >
          Add all published
        </button>
      </div>
      <p className="mb-2 text-xs text-slate-500">
        Unpublished problems can still be solved during this contest by registered students.
        Order = letters A, B, C…
      </p>

      {problems.length === 0 ? (
        <p className="mb-3 rounded-sm border border-dashed border-slate-700 px-3 py-4 text-center text-xs text-slate-500">
          No problems yet — pick from the list below.
        </p>
      ) : (
        <ul className="mb-3 space-y-2">
          {problems.map((row, idx) => {
            const meta = catalogProblems.find((p) => p.id === row.problem_id);
            return (
              <li
                key={row.problem_id}
                className="flex flex-wrap items-center gap-2 rounded-sm border border-slate-800 px-3 py-2 text-xs"
              >
                <span className="w-6 font-mono font-semibold text-emerald-300">
                  {row.letter}
                </span>
                <span className="flex-1 text-slate-300">
                  {meta?.title || `Problem #${row.problem_id}`}
                  {meta && !meta.is_published && (
                    <span className="ml-2 text-amber-400">draft</span>
                  )}
                </span>
                <div className="flex items-center gap-1">
                  <button
                    type="button"
                    aria-label="Move up"
                    disabled={idx === 0}
                    onClick={() => onMoveProblem(idx, -1)}
                    className="cursor-pointer rounded-sm border border-slate-700 px-2 py-0.5 text-slate-300 hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-40"
                  >
                    ↑
                  </button>
                  <button
                    type="button"
                    aria-label="Move down"
                    disabled={idx === problems.length - 1}
                    onClick={() => onMoveProblem(idx, 1)}
                    className="cursor-pointer rounded-sm border border-slate-700 px-2 py-0.5 text-slate-300 hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-40"
                  >
                    ↓
                  </button>
                  <button
                    type="button"
                    onClick={() => onRemoveProblem(idx)}
                    aria-label={`Remove problem ${row.letter}`}
                    className="cursor-pointer px-2 text-red-300 hover:text-red-200"
                  >
                    Remove
                  </button>
                </div>
              </li>
            );
          })}
        </ul>
      )}

      <input
        className="mb-2 w-full rounded-sm border border-slate-700 bg-slate-900 px-3 py-1.5 text-sm"
        placeholder="Search problems to add…"
        aria-label="Search problems to add"
        value={problemSearch}
        onChange={(e) => setProblemSearch(e.target.value)}
      />
      <ul
        aria-label="Problems available to add"
        className="max-h-40 space-y-1 overflow-y-auto rounded-sm border border-slate-800 p-2"
      >
        {filteredAvailable.length === 0 ? (
          <li className="px-2 py-1 text-xs text-slate-500">
            {available.length === 0 ? "All problems are already added." : "No matches."}
          </li>
        ) : (
          filteredAvailable.map((p) => (
            <li key={p.id}>
              <button
                type="button"
                onClick={() => onAddProblem(p.id)}
                className="flex w-full cursor-pointer items-center justify-between gap-2 rounded-sm px-2 py-1.5 text-left text-xs text-slate-300 hover:bg-slate-800"
              >
                <span>
                  {p.title}
                  {!p.is_published && (
                    <span className="ml-2 text-amber-400">draft</span>
                  )}
                </span>
                <span className="text-emerald-400">Add</span>
              </button>
            </li>
          ))
        )}
      </ul>
    </div>
  );
}
