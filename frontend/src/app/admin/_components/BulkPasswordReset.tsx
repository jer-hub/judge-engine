"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";

import { ConfirmDialog } from "@/components/ConfirmDialog";
import { formatApiErrorPayload } from "@/lib/admin";
import { ApiError, apiFetch } from "@/lib/api";

type ResetRow = {
  username: string;
  first_name: string;
  last_name: string;
  class_section: string;
  password: string;
};

function csvCell(value: string) {
  // Quote every cell; also defuse formula-looking text (CSV injection).
  const text = /^[=+\-@\t\r]/.test(value) ? `'${value}` : value;
  return `"${text.replace(/"/g, '""')}"`;
}

function downloadCsv(rows: ResetRow[], section: string) {
  const lines = [
    ["Username", "First name", "Last name", "Section", "New password"],
    ...rows.map((r) => [r.username, r.first_name, r.last_name, r.class_section, r.password]),
  ].map((cols) => cols.map(csvCell).join(","));
  const blob = new Blob(["﻿" + lines.join("\r\n")], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `passwords-${section.replace(/[^\w-]+/g, "-") || "section"}.csv`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

/** Reset every student in a class section to a new random password. The
 *  passwords are shown once: print them or download the CSV before leaving. */
export function BulkPasswordReset() {
  const [section, setSection] = useState("");
  const [confirming, setConfirming] = useState(false);
  const [rows, setRows] = useState<ResetRow[] | null>(null);

  const reset = useMutation({
    mutationFn: () =>
      apiFetch<{ count: number; results: ResetRow[] }>("/users/bulk-reset-password/", {
        method: "POST",
        body: JSON.stringify({ section: section.trim() }),
      }),
    onSuccess: (data) => {
      setConfirming(false);
      setRows(data.results);
    },
    onError: () => setConfirming(false),
  });

  return (
    <div className="space-y-3 rounded-xl border border-slate-800 bg-slate-950/50 p-4 text-sm">
      <p className="text-slate-300">Reset a whole section&apos;s passwords</p>
      <div className="flex flex-wrap items-center gap-2">
        <input
          aria-label="Class section"
          placeholder="Class section, e.g. BSIT-1A"
          value={section}
          onChange={(e) => setSection(e.target.value)}
          className="rounded border border-slate-700 bg-slate-900 px-3 py-1.5"
        />
        <button
          type="button"
          onClick={() => setConfirming(true)}
          disabled={!section.trim() || reset.isPending}
          className="cursor-pointer rounded bg-amber-500 px-3 py-1.5 font-medium text-slate-950 hover:bg-amber-400 disabled:opacity-50"
        >
          {reset.isPending ? "Resetting…" : "Generate new passwords"}
        </button>
        <span className="text-xs text-slate-500">Students only; signs them out everywhere.</span>
      </div>
      {reset.isError && (
        <p className="text-xs text-red-300">
          {reset.error instanceof ApiError
            ? formatApiErrorPayload(reset.error.payload, reset.error.message)
            : reset.error.message}
        </p>
      )}

      {rows && (
        <div className="space-y-2">
          <p className="text-xs text-amber-200">
            {rows.length} password{rows.length === 1 ? "" : "s"} reset. They are shown only now: print
            or download them before closing this.
          </p>
          <div className="flex gap-2 print:hidden">
            <button
              type="button"
              onClick={() => window.print()}
              className="cursor-pointer rounded border border-slate-700 px-3 py-1 text-xs hover:bg-slate-800"
            >
              Print
            </button>
            <button
              type="button"
              onClick={() => downloadCsv(rows, section)}
              className="cursor-pointer rounded border border-slate-700 px-3 py-1 text-xs hover:bg-slate-800"
            >
              Download CSV
            </button>
            <button
              type="button"
              onClick={() => setRows(null)}
              className="cursor-pointer rounded border border-slate-700 px-3 py-1 text-xs text-slate-400 hover:bg-slate-800"
            >
              Done
            </button>
          </div>
          <table className="w-full text-left text-xs">
            <thead className="text-slate-400">
              <tr>
                <th className="py-1">Username</th>
                <th>Name</th>
                <th>Section</th>
                <th>New password</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.username} className="border-t border-slate-800">
                  <td className="py-1 font-medium text-white">{r.username}</td>
                  <td>{[r.first_name, r.last_name].filter(Boolean).join(" ") || "—"}</td>
                  <td>{r.class_section}</td>
                  <td className="font-mono text-emerald-200">{r.password}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <ConfirmDialog
        open={confirming}
        title="Reset passwords?"
        body={`Every student in section “${section.trim()}” gets a new random password and is signed out. Their current passwords stop working.`}
        confirmLabel="Reset passwords"
        danger
        busy={reset.isPending}
        onCancel={() => setConfirming(false)}
        onConfirm={() => reset.mutate()}
      />
    </div>
  );
}
