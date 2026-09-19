"use client";

import { useParams, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";

import { CodeEditor, JAVA_STUB } from "@/components/CodeEditor";
import { StatementContent } from "@/components/StatementContent";
import { SubmissionStatus, VerdictBadge } from "@/components/SubmissionStatus";
import { ApiError, apiFetch } from "@/lib/api";
import type { ProblemDetail, RunPreview, Submission } from "@/lib/types";

function ProblemDetailInner() {
  const params = useParams<{ slug: string }>();
  const search = useSearchParams();
  const contestId = search.get("contest");
  const slug = params.slug;
  const [code, setCode] = useState(JAVA_STUB);
  const [stdin, setStdin] = useState("");
  const [stdinReady, setStdinReady] = useState(false);
  const [submissionId, setSubmissionId] = useState<number | null>(null);
  const [runResult, setRunResult] = useState<RunPreview | null>(null);

  const { data: problem, isLoading, error } = useQuery({
    queryKey: ["problem", slug],
    queryFn: () => apiFetch<ProblemDetail>(`/problems/${slug}/`),
  });

  useEffect(() => {
    const key = `draft:${slug}`;
    const saved = localStorage.getItem(key);
    if (saved) setCode(saved);
  }, [slug]);

  useEffect(() => {
    if (!slug) return;
    localStorage.setItem(`draft:${slug}`, code);
  }, [code, slug]);

  useEffect(() => {
    if (!problem || stdinReady) return;
    const sample = problem.sample_tests[0]?.input_data ?? "";
    setStdin(sample);
    setStdinReady(true);
  }, [problem, stdinReady]);

  const submit = useMutation({
    mutationFn: () =>
      apiFetch<Submission>("/submissions/", {
        method: "POST",
        body: JSON.stringify({
          problem: problem!.id,
          contest: contestId ? Number(contestId) : null,
          source_code: code,
          language: "java",
        }),
      }),
    onSuccess: (data) => setSubmissionId(data.id),
  });

  const run = useMutation({
    mutationFn: () =>
      apiFetch<RunPreview>("/runs/", {
        method: "POST",
        body: JSON.stringify({
          problem: problem!.id,
          source_code: code,
          language: "java",
          stdin,
        }),
      }),
    onSuccess: (data) => setRunResult(data),
  });

  if (isLoading) return <p className="text-slate-400">Loading problem…</p>;
  if (error || !problem) {
    const unavailable =
      error instanceof ApiError
        ? error.status === 404
        : (error as Error)?.message?.toLowerCase().includes("not found");
    return (
      <p className="text-red-300">
        {unavailable
          ? "This problem is not available. It may be unpublished or the link is incorrect."
          : (error as Error)?.message || "Not found"}
      </p>
    );
  }

  const busy = submit.isPending || run.isPending;

  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <section className="space-y-4">
        <div>
          <h1 className="text-3xl font-semibold text-white">{problem.title}</h1>
          <p className="mt-1 text-sm text-slate-400">
            {problem.time_limit_ms} ms · {problem.memory_limit_mb} MB ·{" "}
            <span className="capitalize">{problem.difficulty}</span>
            {contestId ? ` · Contest #${contestId}` : ""}
            {" · "}
            {problem.run_all_tests
              ? "Runs all tests (feedback)"
              : "Stop on first failure"}
          </p>
          <p className="mt-1 text-xs text-slate-500">
            Scoreboard scoring is ICPC binary regardless of this setting.
          </p>
        </div>
        <article className="rounded-xl border border-slate-800 bg-slate-900/40 p-4">
          <StatementContent content={problem.statement} />
        </article>
        {problem.sample_tests.length > 0 && (
          <div className="space-y-3">
            <h2 className="text-lg font-medium">Sample tests</h2>
            {problem.sample_tests.map((t) => (
              <div key={t.id} className="grid gap-2 sm:grid-cols-2">
                <pre className="overflow-x-auto rounded bg-slate-900 p-3 text-xs">
                  <div className="mb-1 flex items-center justify-between text-slate-500">
                    <span>Input</span>
                    <button
                      type="button"
                      className="cursor-pointer text-emerald-400 hover:underline"
                      onClick={() => void navigator.clipboard.writeText(t.input_data)}
                    >
                      Copy
                    </button>
                  </div>
                  {t.input_data}
                </pre>
                <pre className="overflow-x-auto rounded bg-slate-900 p-3 text-xs">
                  <div className="mb-1 flex items-center justify-between text-slate-500">
                    <span>Output</span>
                    <button
                      type="button"
                      className="cursor-pointer text-emerald-400 hover:underline"
                      onClick={() => void navigator.clipboard.writeText(t.expected_output)}
                    >
                      Copy
                    </button>
                  </div>
                  {t.expected_output}
                </pre>
              </div>
            ))}
          </div>
        )}
      </section>

      <section className="space-y-4">
        <CodeEditor value={code} onChange={setCode} />

        <div>
          <div className="mb-1 flex items-center justify-between text-sm">
            <label htmlFor="stdin" className="text-slate-300">
              Custom input (stdin)
            </label>
            {problem.sample_tests[0] && (
              <button
                type="button"
                className="text-xs text-emerald-400 hover:underline"
                onClick={() => setStdin(problem.sample_tests[0].input_data)}
              >
                Load sample
              </button>
            )}
          </div>
          <textarea
            id="stdin"
            value={stdin}
            onChange={(e) => setStdin(e.target.value)}
            rows={4}
            spellCheck={false}
            className="w-full rounded-lg border border-slate-800 bg-slate-950 px-3 py-2 font-mono text-xs text-slate-200"
            placeholder="Input fed to your program…"
          />
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <button
            type="button"
            onClick={() => run.mutate()}
            disabled={busy}
            className="rounded border border-slate-600 bg-slate-900 px-4 py-2 font-medium hover:bg-slate-800 disabled:opacity-60"
          >
            {run.isPending ? "Running…" : "Run"}
          </button>
          <button
            type="button"
            onClick={() => submit.mutate()}
            disabled={busy}
            className="rounded bg-emerald-600 px-4 py-2 font-medium hover:bg-emerald-500 disabled:opacity-60"
          >
            {submit.isPending ? "Submitting…" : "Submit Java"}
          </button>
          {(run.isError || submit.isError) && (
            <span className="text-sm text-red-300">
              {((run.error || submit.error) as Error).message}
            </span>
          )}
        </div>

        {runResult && (
          <div className="space-y-2 rounded-lg border border-slate-800 bg-slate-900/50 p-4">
            <div className="flex items-center justify-between gap-3">
              <h3 className="font-medium text-white">Preview output</h3>
              <div className="flex items-center gap-2 text-xs text-slate-400">
                <VerdictBadge status={runResult.status === "OK" ? "Accepted" : runResult.status} />
                {runResult.execution_time_ms != null && (
                  <span>{runResult.execution_time_ms} ms</span>
                )}
              </div>
            </div>
            {runResult.compile_error && (
              <pre className="overflow-x-auto rounded bg-red-950/40 p-3 text-xs text-red-200">
                {runResult.compile_error}
              </pre>
            )}
            <div>
              <div className="mb-1 text-xs uppercase tracking-wide text-slate-500">stdout</div>
              <pre className="max-h-48 overflow-auto rounded bg-slate-950 p-3 text-xs text-emerald-100 whitespace-pre-wrap">
                {runResult.stdout || "(empty)"}
              </pre>
            </div>
            {runResult.stderr && (
              <div>
                <div className="mb-1 text-xs uppercase tracking-wide text-slate-500">stderr</div>
                <pre className="max-h-32 overflow-auto rounded bg-slate-950 p-3 text-xs text-amber-100 whitespace-pre-wrap">
                  {runResult.stderr}
                </pre>
              </div>
            )}
            <p className="text-xs text-slate-500">
              Run is a dry preview — it does not count as a submission or affect the scoreboard.
            </p>
          </div>
        )}

        <SubmissionStatus submissionId={submissionId} />
      </section>
    </div>
  );
}

export default function ProblemDetailPage() {
  return (
    <Suspense fallback={<p className="text-slate-400">Loading…</p>}>
      <ProblemDetailInner />
    </Suspense>
  );
}
