"use client";

import { useState } from "react";

import type { TestCase } from "@/lib/test-cases";

type Props = {
  testCase: TestCase;
  busy: boolean;
  onSave: (patch: Partial<TestCase>) => void;
  onDelete: () => void;
};

export function TestCaseRow({ testCase, busy, onSave, onDelete }: Props) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState({
    input_data: testCase.input_data,
    expected_output: testCase.expected_output,
    is_sample: testCase.is_sample,
    points: testCase.points,
    order: testCase.order,
  });

  if (!editing) {
    return (
      <div className="flex flex-wrap items-start justify-between gap-2 rounded border border-slate-800 bg-slate-900/40 px-3 py-2 text-xs">
        <div className="min-w-0 flex-1">
          <p className="text-slate-300">
            #{testCase.order}{" "}
            <span
              className={
                testCase.is_sample ? "text-emerald-400" : "text-slate-500"
              }
            >
              {testCase.is_sample ? "sample" : "hidden"}
            </span>{" "}
            · {testCase.points} pts
          </p>
          <pre className="mt-1 max-h-16 overflow-auto text-[11px] text-slate-500">
            in: {testCase.input_data.slice(0, 80) || "(empty)"}
          </pre>
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => setEditing(true)}
            className="cursor-pointer text-slate-300 transition hover:text-white"
          >
            Edit
          </button>
          <button
            type="button"
            disabled={busy}
            onClick={onDelete}
            className="cursor-pointer text-red-300 transition hover:text-red-200 disabled:opacity-50"
          >
            Delete
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="grid gap-2 rounded border border-emerald-900/50 bg-slate-900/60 p-3 text-xs sm:grid-cols-2">
      <label className="block sm:col-span-2">
        <span className="mb-1 block text-slate-400">Input</span>
        <textarea
          className="min-h-[56px] w-full rounded border border-slate-700 bg-slate-950 px-2 py-1 font-mono"
          value={draft.input_data}
          onChange={(e) => setDraft((p) => ({ ...p, input_data: e.target.value }))}
        />
      </label>
      <label className="block sm:col-span-2">
        <span className="mb-1 block text-slate-400">Expected</span>
        <textarea
          className="min-h-[56px] w-full rounded border border-slate-700 bg-slate-950 px-2 py-1 font-mono"
          value={draft.expected_output}
          onChange={(e) =>
            setDraft((p) => ({ ...p, expected_output: e.target.value }))
          }
        />
      </label>
      <label className="flex items-center gap-2">
        <input
          type="checkbox"
          checked={draft.is_sample}
          onChange={(e) => setDraft((p) => ({ ...p, is_sample: e.target.checked }))}
          className="cursor-pointer"
        />
        Sample
      </label>
      <label className="block">
        <span className="mb-1 block text-slate-400">Order / points</span>
        <div className="flex gap-2">
          <input
            type="number"
            className="w-full rounded border border-slate-700 bg-slate-950 px-2 py-1"
            value={draft.order}
            onChange={(e) => setDraft((p) => ({ ...p, order: Number(e.target.value) }))}
          />
          <input
            type="number"
            min={0}
            className="w-full rounded border border-slate-700 bg-slate-950 px-2 py-1"
            value={draft.points}
            onChange={(e) => setDraft((p) => ({ ...p, points: Number(e.target.value) }))}
          />
        </div>
      </label>
      <div className="flex gap-2 sm:col-span-2">
        <button
          type="button"
          disabled={busy}
          onClick={() => {
            onSave(draft);
            setEditing(false);
          }}
          className="cursor-pointer rounded bg-emerald-500 px-3 py-1 font-medium text-slate-950 hover:bg-emerald-400 disabled:opacity-60"
        >
          Save
        </button>
        <button
          type="button"
          onClick={() => {
            setDraft({
              input_data: testCase.input_data,
              expected_output: testCase.expected_output,
              is_sample: testCase.is_sample,
              points: testCase.points,
              order: testCase.order,
            });
            setEditing(false);
          }}
          className="cursor-pointer rounded border border-slate-700 px-3 py-1 text-slate-300 hover:bg-slate-800"
        >
          Cancel
        </button>
      </div>
    </div>
  );
}
