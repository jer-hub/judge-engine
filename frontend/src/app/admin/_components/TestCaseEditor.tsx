"use client";

import { FormEvent, useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { formatApiErrorPayload } from "@/lib/admin";
import { ApiError } from "@/lib/api";
import {
  createTestCase,
  deleteTestCase,
  listTestCases,
  type TestCase,
  updateTestCase,
} from "@/lib/test-cases";

import { TestCaseRow } from "./TestCaseRow";

type Props = {
  problemId: number;
  problemTitle: string;
  onClose: () => void;
};

const emptyDraft = {
  order: 0,
  input_data: "",
  expected_output: "",
  is_sample: true,
  points: 1,
};

export function TestCaseEditor({ problemId, problemTitle, onClose }: Props) {
  const queryClient = useQueryClient();
  const [draft, setDraft] = useState(emptyDraft);
  const [error, setError] = useState<string | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ["admin", "test-cases", problemId],
    queryFn: () => listTestCases(problemId),
  });

  useEffect(() => {
    const count = data?.results?.length ?? 0;
    setDraft((prev) => ({ ...prev, order: count }));
  }, [data?.results?.length]);

  function invalidate() {
    void queryClient.invalidateQueries({ queryKey: ["admin", "test-cases", problemId] });
    void queryClient.invalidateQueries({ queryKey: ["admin", "problems"] });
  }

  const createMutation = useMutation({
    mutationFn: () =>
      createTestCase({
        problem: problemId,
        ...draft,
      }),
    onSuccess: () => {
      setDraft({ ...emptyDraft, order: (data?.results?.length ?? 0) + 1 });
      setError(null);
      invalidate();
    },
    onError: (err: Error) => {
      setError(
        err instanceof ApiError
          ? formatApiErrorPayload(err.payload, err.message)
          : err.message,
      );
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, patch }: { id: number; patch: Partial<TestCase> }) =>
      updateTestCase(id, patch),
    onSuccess: () => {
      setError(null);
      invalidate();
    },
    onError: (err: Error) => {
      setError(
        err instanceof ApiError
          ? formatApiErrorPayload(err.payload, err.message)
          : err.message,
      );
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => deleteTestCase(id),
    onSuccess: () => {
      setError(null);
      invalidate();
    },
    onError: (err: Error) => {
      setError(err.message);
    },
  });

  function onAdd(e: FormEvent) {
    e.preventDefault();
    if (!draft.input_data.trim() || !draft.expected_output.trim()) {
      setError("Input and expected output are required.");
      return;
    }
    createMutation.mutate();
  }

  return (
    <div className="mt-3 space-y-3 rounded-lg border border-slate-700 bg-slate-950/60 p-4">
      <div className="flex items-center justify-between gap-3">
        <h4 className="text-sm font-medium text-white">
          Test cases — {problemTitle}
        </h4>
        <button
          type="button"
          onClick={onClose}
          className="cursor-pointer text-xs text-slate-400 transition hover:text-white"
        >
          Close
        </button>
      </div>

      {isLoading && <p className="text-xs text-slate-500">Loading…</p>}
      {error && <p className="text-xs text-red-300">{error}</p>}

      <div className="space-y-2">
        {(data?.results ?? []).map((tc) => (
          <TestCaseRow
            key={tc.id}
            testCase={tc}
            busy={updateMutation.isPending || deleteMutation.isPending}
            onSave={(patch) => updateMutation.mutate({ id: tc.id, patch })}
            onDelete={() => deleteMutation.mutate(tc.id)}
          />
        ))}
        {!isLoading && (data?.results?.length ?? 0) === 0 && (
          <p className="text-xs text-slate-500">No test cases yet. Add a sample below.</p>
        )}
      </div>

      <form onSubmit={onAdd} className="grid gap-2 border-t border-slate-800 pt-3 sm:grid-cols-2">
        <label className="block text-xs sm:col-span-2">
          <span className="mb-1 block text-slate-400">Input</span>
          <textarea
            className="min-h-[64px] w-full rounded border border-slate-700 bg-slate-900 px-2 py-1.5 font-mono text-xs"
            value={draft.input_data}
            onChange={(e) => setDraft((p) => ({ ...p, input_data: e.target.value }))}
          />
        </label>
        <label className="block text-xs sm:col-span-2">
          <span className="mb-1 block text-slate-400">Expected output</span>
          <textarea
            className="min-h-[64px] w-full rounded border border-slate-700 bg-slate-900 px-2 py-1.5 font-mono text-xs"
            value={draft.expected_output}
            onChange={(e) =>
              setDraft((p) => ({ ...p, expected_output: e.target.value }))
            }
          />
        </label>
        <label className="flex items-center gap-2 text-xs">
          <input
            type="checkbox"
            checked={draft.is_sample}
            onChange={(e) => setDraft((p) => ({ ...p, is_sample: e.target.checked }))}
            className="cursor-pointer"
          />
          Sample (visible to students)
        </label>
        <label className="block text-xs">
          <span className="mb-1 block text-slate-400">Points</span>
          <input
            type="number"
            min={0}
            className="w-full rounded border border-slate-700 bg-slate-900 px-2 py-1.5"
            value={draft.points}
            onChange={(e) => setDraft((p) => ({ ...p, points: Number(e.target.value) }))}
          />
        </label>
        <div className="sm:col-span-2">
          <button
            type="submit"
            disabled={createMutation.isPending}
            className="cursor-pointer rounded bg-emerald-500 px-3 py-1.5 text-xs font-medium text-slate-950 transition hover:bg-emerald-400 disabled:opacity-60"
          >
            {createMutation.isPending ? "Adding…" : "Add test case"}
          </button>
        </div>
      </form>
    </div>
  );
}
