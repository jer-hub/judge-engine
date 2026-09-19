"use client";

import { useRef, useState } from "react";
import { useMutation } from "@tanstack/react-query";

import { formatApiErrorPayload } from "@/lib/admin";
import { ApiError, apiFetch } from "@/lib/api";
import type { UserImportResult } from "@/lib/types";

const SAMPLE_HEADER =
  "username,password,first_name,last_name,email,school_id,class_section";

const MAX_CHARS = 100_000;

type Props = {
  onImported: () => void;
};

export function AccountsImport({ onImported }: Props) {
  const fileRef = useRef<HTMLInputElement>(null);
  const [csvText, setCsvText] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<UserImportResult | null>(null);

  const importMutation = useMutation({
    mutationFn: (dryRun: boolean) =>
      apiFetch<UserImportResult>("/users/import/", {
        method: "POST",
        body: JSON.stringify({ csv_text: csvText, dry_run: dryRun }),
      }),
    onSuccess: (data, dryRun) => {
      setError(null);
      setResult(data);
      if (!dryRun && data.created > 0) {
        onImported();
      }
    },
    onError: (err: Error) => {
      setResult(null);
      setError(
        err instanceof ApiError
          ? formatApiErrorPayload(err.payload, err.message)
          : err.message,
      );
    },
  });

  async function onFileChange(file: File | null) {
    if (!file) return;
    const text = await file.text();
    if (text.length > MAX_CHARS) {
      setError(`CSV is too large (max ${MAX_CHARS.toLocaleString()} characters).`);
      return;
    }
    setCsvText(text);
    setError(null);
    setResult(null);
  }

  function run(dryRun: boolean) {
    setError(null);
    if (!csvText.trim()) {
      setError("Paste or upload a CSV first.");
      return;
    }
    if (csvText.length > MAX_CHARS) {
      setError(`CSV is too large (max ${MAX_CHARS.toLocaleString()} characters).`);
      return;
    }
    importMutation.mutate(dryRun);
  }

  return (
    <div className="space-y-3 rounded-xl border border-slate-800 bg-slate-950/50 p-4">
      <div>
        <h4 className="font-medium text-white">Import students from CSV</h4>
        <p className="mt-1 text-xs text-slate-400">
          Required columns: <code className="text-slate-300">username</code>,{" "}
          <code className="text-slate-300">password</code> (min 8 chars). Optional:{" "}
          first_name, last_name, email, school_id, class_section. All imported accounts
          are students. Existing usernames are skipped (passwords unchanged).
        </p>
        <p className="mt-2 break-all font-mono text-[11px] text-slate-500">{SAMPLE_HEADER}</p>
      </div>

      <div className="flex flex-wrap gap-2">
        <input
          ref={fileRef}
          type="file"
          accept=".csv,text/csv"
          className="hidden"
          onChange={(e) => void onFileChange(e.target.files?.[0] ?? null)}
        />
        <button
          type="button"
          onClick={() => fileRef.current?.click()}
          className="cursor-pointer rounded border border-slate-700 px-3 py-1.5 text-xs text-slate-200 hover:border-slate-500"
        >
          Upload .csv
        </button>
        <button
          type="button"
          onClick={() => {
            setCsvText(`${SAMPLE_HEADER}\n`);
            setResult(null);
            setError(null);
          }}
          className="cursor-pointer rounded border border-slate-700 px-3 py-1.5 text-xs text-slate-200 hover:border-slate-500"
        >
          Insert header
        </button>
      </div>

      <textarea
        className="min-h-[140px] w-full rounded border border-slate-700 bg-slate-900 px-3 py-2 font-mono text-xs"
        placeholder={`${SAMPLE_HEADER}\nalice,pass12345,Alice,Tan,alice@school.edu,S001,7A`}
        value={csvText}
        onChange={(e) => {
          setCsvText(e.target.value);
          setResult(null);
        }}
        spellCheck={false}
      />

      {error && <p className="text-sm text-red-300">{error}</p>}

      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          disabled={importMutation.isPending}
          onClick={() => run(true)}
          className="cursor-pointer rounded-lg border border-slate-600 px-3 py-2 text-sm text-slate-200 hover:border-slate-400 disabled:opacity-60"
        >
          {importMutation.isPending ? "Working…" : "Preview"}
        </button>
        <button
          type="button"
          disabled={importMutation.isPending}
          onClick={() => run(false)}
          className="cursor-pointer rounded-lg bg-emerald-500 px-3 py-2 text-sm font-medium text-slate-950 hover:bg-emerald-400 disabled:opacity-60"
        >
          {importMutation.isPending ? "Working…" : "Import"}
        </button>
      </div>

      {result && (
        <div className="rounded-lg border border-slate-800 bg-slate-900/60 p-3 text-sm">
          <p className="text-slate-200">
            {result.dry_run ? "Preview" : "Import"}:{" "}
            <span className="text-emerald-300">{result.created} created</span>
            {result.dry_run ? " (not saved)" : ""},{" "}
            <span className="text-sky-300">{result.skipped} skipped</span>,{" "}
            <span className="text-amber-300">{result.failed} failed</span>
          </p>
          {result.created_usernames.length > 0 && (
            <p className="mt-1 text-xs text-slate-500">
              {result.dry_run ? "Would create" : "Created"}:{" "}
              {result.created_usernames.slice(0, 20).join(", ")}
              {result.created_usernames.length > 20
                ? ` (+${result.created_usernames.length - 20} more)`
                : ""}
            </p>
          )}
          {result.errors.length > 0 && (
            <div className="mt-3 overflow-x-auto">
              <table className="w-full min-w-[420px] text-left text-xs">
                <thead className="text-slate-500">
                  <tr>
                    <th className="py-1 pr-3">Row</th>
                    <th className="py-1 pr-3">Username</th>
                    <th className="py-1">Error</th>
                  </tr>
                </thead>
                <tbody>
                  {result.errors.map((e) => (
                    <tr key={`${e.row}-${e.username}`} className="border-t border-slate-800">
                      <td className="py-1 pr-3 font-mono text-slate-400">{e.row}</td>
                      <td className="py-1 pr-3 text-slate-300">{e.username || "—"}</td>
                      <td className="py-1 text-amber-200">{e.error}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
