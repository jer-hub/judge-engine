"use client";

import Link from "next/link";
import { FormEvent, useEffect, useMemo, useState } from "react";
import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { ConfirmDialog } from "@/components/ConfirmDialog";
import { EmptyState } from "@/components/EmptyState";
import { Pagination } from "@/components/Pagination";
import { useDebouncedValue } from "@/hooks/useDebouncedValue";
import { formatApiErrorPayload } from "@/lib/admin";
import { ApiError, apiFetch } from "@/lib/api";
import { buildListQuery } from "@/lib/pagination";
import type { ContestEditorPhase, ContestListItem, Paginated } from "@/lib/types";

import { ContestEditor } from "./ContestEditor";
import { MagnifyingGlassIcon } from "./icons";

type CreateContestBody = {
  title: string;
  description: string;
  start_time: string;
  end_time: string;
  is_public: boolean;
  freeze_scoreboard_minutes_before_end: number;
};

type StatusFilter = "all" | "upcoming" | "active" | "past" | "archived";

type Props = {
  statusFilter: StatusFilter;
  contestId: number | null;
  phase: ContestEditorPhase;
  onStatusFilterChange: (status: StatusFilter) => void;
  onContestChange: (id: number | null) => void;
  onPhaseChange: (phase: ContestEditorPhase) => void;
  onViewSubmissions?: (contestId: number) => void;
};

const PAGE_SIZE = 20;

function toLocalInputValue(date: Date) {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

function defaultWindow() {
  const start = new Date();
  start.setMinutes(start.getMinutes() + 30);
  const end = new Date(start);
  end.setHours(end.getHours() + 2);
  return {
    start_time: toLocalInputValue(start),
    end_time: toLocalInputValue(end),
  };
}

function statusTone(status: ContestListItem["status"] | "archived") {
  if (status === "active") return "bg-emerald-900/50 text-emerald-300";
  if (status === "upcoming") return "bg-sky-900/50 text-sky-200";
  if (status === "archived") return "bg-slate-800 text-slate-500";
  return "bg-slate-800 text-slate-400";
}

function formatCompactWindow(startIso: string, endIso: string): string {
  const start = new Date(startIso);
  const end = new Date(endIso);
  if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime())) return "—";
  const sameDay =
    start.getFullYear() === end.getFullYear() &&
    start.getMonth() === end.getMonth() &&
    start.getDate() === end.getDate();
  const d = (x: Date) =>
    x.toLocaleDateString(undefined, { month: "numeric", day: "numeric", year: "numeric" });
  const t = (x: Date) =>
    x.toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" });
  if (sameDay) return `${d(start)} ${t(start)} → ${t(end)}`;
  return `${d(start)} ${t(start)} → ${d(end)} ${t(end)}`;
}

const STATUS_CHIPS: Array<{ id: StatusFilter; label: string }> = [
  { id: "all", label: "All" },
  { id: "upcoming", label: "Upcoming" },
  { id: "active", label: "Active" },
  { id: "past", label: "Past" },
  { id: "archived", label: "Archived" },
];

export function ContestsPanel({
  statusFilter,
  contestId: editId,
  phase,
  onStatusFilterChange,
  onContestChange,
  onPhaseChange,
  onViewSubmissions,
}: Props) {
  const queryClient = useQueryClient();
  const windowDefaults = defaultWindow();

  const setStatusFilter = onStatusFilterChange;
  const setEditId = onContestChange;
  const setPhase = onPhaseChange;

  const [formOpen, setFormOpen] = useState(false);
  const [search, setSearch] = useState("");
  const debouncedSearch = useDebouncedValue(search, 300);
  const [page, setPage] = useState(1);
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [confirm, setConfirm] = useState<
    | { type: "archive"; contest: ContestListItem }
    | { type: "delete"; contest: ContestListItem }
    | { type: "bulk"; action: "archive" | "set_public" | "set_invite_only" }
    | null
  >(null);
  const [bulkError, setBulkError] = useState<string | null>(null);
  const [form, setForm] = useState<CreateContestBody>({
    title: "",
    description: "",
    start_time: windowDefaults.start_time,
    end_time: windowDefaults.end_time,
    is_public: true,
    freeze_scoreboard_minutes_before_end: 0,
  });
  const [formError, setFormError] = useState<string | null>(null);

  useEffect(() => {
    setPage(1);
    setSelected(new Set());
  }, [debouncedSearch, statusFilter]);

  const queryPath = buildListQuery("/contests/", {
    page,
    page_size: PAGE_SIZE,
    search: debouncedSearch.trim() || undefined,
    status: statusFilter === "all" ? undefined : statusFilter,
  });

  const { data, isLoading, error, isFetching } = useQuery({
    queryKey: [
      "admin",
      "contests",
      "list",
      { page, search: debouncedSearch, status: statusFilter },
    ],
    queryFn: () => apiFetch<Paginated<ContestListItem>>(queryPath),
    placeholderData: keepPreviousData,
  });

  const rows = data?.results ?? [];
  const allSelected = rows.length > 0 && rows.every((c) => selected.has(c.id));

  const createMutation = useMutation({
    mutationFn: (body: CreateContestBody) =>
      apiFetch<ContestListItem>("/contests/", {
        method: "POST",
        body: JSON.stringify({
          ...body,
          start_time: new Date(body.start_time).toISOString(),
          end_time: new Date(body.end_time).toISOString(),
        }),
      }),
    onSuccess: (created) => {
      setFormOpen(false);
      setFormError(null);
      const next = defaultWindow();
      setForm({
        title: "",
        description: "",
        start_time: next.start_time,
        end_time: next.end_time,
        is_public: true,
        freeze_scoreboard_minutes_before_end: 0,
      });
      void queryClient.invalidateQueries({ queryKey: ["admin", "contests"] });
      void queryClient.invalidateQueries({ queryKey: ["contests"] });
      setPhase("setup");
      setEditId(created.id);
    },
    onError: (err: Error) => {
      if (err instanceof ApiError) {
        setFormError(formatApiErrorPayload(err.payload, err.message));
      } else {
        setFormError(err.message);
      }
    },
  });

  const archiveMutation = useMutation({
    mutationFn: ({ id, archived }: { id: number; archived: boolean }) =>
      apiFetch(`/contests/${id}/archive/`, {
        method: "POST",
        body: JSON.stringify({ archived }),
      }),
    onSuccess: () => {
      setConfirm(null);
      void queryClient.invalidateQueries({ queryKey: ["admin", "contests"] });
      void queryClient.invalidateQueries({ queryKey: ["contests"] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) =>
      apiFetch(`/contests/${id}/`, { method: "DELETE" }),
    onSuccess: () => {
      setConfirm(null);
      if (editId != null) setEditId(null);
      void queryClient.invalidateQueries({ queryKey: ["admin", "contests"] });
      void queryClient.invalidateQueries({ queryKey: ["contests"] });
    },
  });

  const bulkMutation = useMutation({
    mutationFn: (body: { ids: number[]; action: string }) =>
      apiFetch<{ updated: number }>("/contests/bulk/", {
        method: "POST",
        body: JSON.stringify(body),
      }),
    onSuccess: () => {
      setBulkError(null);
      setConfirm(null);
      setSelected(new Set());
      void queryClient.invalidateQueries({ queryKey: ["admin", "contests"] });
      void queryClient.invalidateQueries({ queryKey: ["contests"] });
    },
    onError: (err: Error) => {
      setConfirm(null);
      setBulkError(
        err instanceof ApiError
          ? formatApiErrorPayload(err.payload, err.message)
          : err.message,
      );
    },
  });

  const bulkLabels: Record<"archive" | "set_public" | "set_invite_only", string> = {
    archive: "Archive",
    set_public: "Set public",
    set_invite_only: "Set invite-only",
  };

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    setFormError(null);
    if (!form.title.trim()) {
      setFormError("Title is required.");
      return;
    }
    const start = new Date(form.start_time);
    const end = new Date(form.end_time);
    if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime())) {
      setFormError("Start and end times must be valid.");
      return;
    }
    if (end <= start) {
      setFormError("End time must be after start time.");
      return;
    }
    createMutation.mutate(form);
  }

  function toggleAll() {
    if (allSelected) {
      setSelected(new Set());
      return;
    }
    setSelected(new Set(rows.map((c) => c.id)));
  }

  function toggleOne(id: number) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  const selectedIds = useMemo(() => Array.from(selected), [selected]);

  if (editId != null) {
    return (
      <ContestEditor
        key={editId}
        contestId={editId}
        phase={phase}
        onPhaseChange={setPhase}
        onClose={() => setEditId(null)}
        onViewSubmissions={
          onViewSubmissions ? () => onViewSubmissions(editId) : undefined
        }
      />
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-sm text-slate-400">
          Schedule contests, invite students, and run live ops from Manage.
        </p>
        <button
          type="button"
          onClick={() => setFormOpen((v) => !v)}
          className="cursor-pointer rounded-lg bg-emerald-500 px-3 py-2 text-sm font-medium text-slate-950 transition hover:bg-emerald-400"
        >
          {formOpen ? "Close form" : "New contest"}
        </button>
      </div>

      {formOpen && (
        <form
          onSubmit={onSubmit}
          className="grid gap-3 rounded-xl border border-slate-800 bg-slate-950/50 p-4 sm:grid-cols-2"
        >
          <label className="block text-sm sm:col-span-2">
            <span className="mb-1 block text-slate-400">Title</span>
            <input
              className="w-full rounded-sm border border-slate-700 bg-slate-900 px-3 py-2"
              value={form.title}
              onChange={(e) => setForm((prev) => ({ ...prev, title: e.target.value }))}
              required
            />
          </label>
          <label className="block text-sm sm:col-span-2">
            <span className="mb-1 block text-slate-400">Description</span>
            <textarea
              className="min-h-[80px] w-full rounded-sm border border-slate-700 bg-slate-900 px-3 py-2 text-sm"
              value={form.description}
              onChange={(e) =>
                setForm((prev) => ({ ...prev, description: e.target.value }))
              }
            />
          </label>
          <label className="block text-sm">
            <span className="mb-1 block text-slate-400">Start</span>
            <input
              type="datetime-local"
              className="w-full rounded-sm border border-slate-700 bg-slate-900 px-3 py-2"
              value={form.start_time}
              onChange={(e) =>
                setForm((prev) => ({ ...prev, start_time: e.target.value }))
              }
              required
            />
          </label>
          <label className="block text-sm">
            <span className="mb-1 block text-slate-400">End</span>
            <input
              type="datetime-local"
              className="w-full rounded-sm border border-slate-700 bg-slate-900 px-3 py-2"
              value={form.end_time}
              onChange={(e) => setForm((prev) => ({ ...prev, end_time: e.target.value }))}
              required
            />
          </label>
          <label className="block text-sm">
            <span className="mb-1 block text-slate-400">Freeze (minutes before end)</span>
            <input
              type="number"
              min={0}
              className="w-full rounded-sm border border-slate-700 bg-slate-900 px-3 py-2"
              value={form.freeze_scoreboard_minutes_before_end}
              onChange={(e) =>
                setForm((prev) => ({
                  ...prev,
                  freeze_scoreboard_minutes_before_end: Number(e.target.value),
                }))
              }
            />
          </label>
          <label className="flex items-center gap-2 self-end text-sm">
            <input
              type="checkbox"
              checked={form.is_public}
              onChange={(e) =>
                setForm((prev) => ({ ...prev, is_public: e.target.checked }))
              }
              className="cursor-pointer"
            />
            <span>Public contest</span>
          </label>
          {formError && <p className="text-sm text-red-300 sm:col-span-2">{formError}</p>}
          <div className="sm:col-span-2">
            <button
              type="submit"
              disabled={createMutation.isPending}
              className="cursor-pointer rounded-lg bg-emerald-500 px-4 py-2 text-sm font-medium text-slate-950 transition hover:bg-emerald-400 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {createMutation.isPending ? "Creating…" : "Create & configure"}
            </button>
          </div>
        </form>
      )}

      <div className="flex flex-wrap items-center gap-2">
        <div
          role="group"
          aria-label="Filter by status"
          className="flex flex-wrap gap-1 rounded-lg border border-slate-800 bg-slate-950/50 p-1"
        >
          {STATUS_CHIPS.map((chip) => {
            const selectedChip = statusFilter === chip.id;
            return (
              <button
                key={chip.id}
                type="button"
                onClick={() => setStatusFilter(chip.id)}
                className={`cursor-pointer rounded-md px-2.5 py-1 text-xs font-medium transition ${
                  selectedChip
                    ? "bg-slate-800 text-white"
                    : "text-slate-400 hover:bg-slate-900 hover:text-slate-200"
                }`}
              >
                {chip.label}
              </button>
            );
          })}
        </div>
        <label className="relative min-w-[200px] flex-1">
          <span className="sr-only">Search contests</span>
          <MagnifyingGlassIcon className="pointer-events-none absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
          <input
            className="w-full rounded-sm border border-slate-700 bg-slate-900 py-2 pl-8 pr-3 text-sm"
            placeholder="Search by title…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </label>
        {isFetching && !isLoading && (
          <span className="text-xs text-slate-500">Updating…</span>
        )}
      </div>

      {selectedIds.length > 0 && (
        <div className="flex flex-wrap items-center gap-2 rounded-sm border border-emerald-900/50 bg-emerald-950/20 px-3 py-2 text-xs">
          <span className="text-emerald-200">{selectedIds.length} selected</span>
          <button
            type="button"
            disabled={bulkMutation.isPending}
            onClick={() => setConfirm({ type: "bulk", action: "archive" })}
            className="cursor-pointer rounded-sm border border-slate-700 px-2 py-1 text-slate-200 hover:bg-slate-800 disabled:opacity-50"
          >
            Archive
          </button>
          <button
            type="button"
            disabled={bulkMutation.isPending}
            onClick={() => setConfirm({ type: "bulk", action: "set_public" })}
            className="cursor-pointer rounded-sm border border-slate-700 px-2 py-1 text-slate-200 hover:bg-slate-800 disabled:opacity-50"
          >
            Set public
          </button>
          <button
            type="button"
            disabled={bulkMutation.isPending}
            onClick={() => setConfirm({ type: "bulk", action: "set_invite_only" })}
            className="cursor-pointer rounded-sm border border-slate-700 px-2 py-1 text-slate-200 hover:bg-slate-800 disabled:opacity-50"
          >
            Set invite-only
          </button>
          <button
            type="button"
            onClick={() => setSelected(new Set())}
            className="cursor-pointer text-slate-400 hover:text-white"
          >
            Clear
          </button>
        </div>
      )}
      {bulkError && <p className="text-xs text-red-300">{bulkError}</p>}

      {isLoading && <p className="text-sm text-slate-400">Loading contests…</p>}
      {error && <p className="text-sm text-red-300">{(error as Error).message}</p>}

      {!isLoading && rows.length === 0 ? (
        <EmptyState
          title="No contests yet"
          body="Create a contest, attach problems, and invite your class."
          actionLabel="New contest"
          onAction={() => setFormOpen(true)}
        />
      ) : (
        <>
          <div className="overflow-x-auto rounded-xl border border-slate-800">
            <table className="w-full min-w-[720px] text-left text-sm">
              <thead className="bg-slate-900/80 text-slate-400">
                <tr>
                  <th className="px-3 py-3">
                    <input
                      type="checkbox"
                      checked={allSelected}
                      onChange={toggleAll}
                      aria-label="Select all contests on this page"
                      className="cursor-pointer"
                    />
                  </th>
                  <th className="px-4 py-3 font-medium">Contest</th>
                  <th className="px-4 py-3 font-medium">Window</th>
                  <th className="px-4 py-3 font-medium">Status</th>
                  <th className="px-4 py-3 font-medium">Problems</th>
                  <th className="px-4 py-3 font-medium">Actions</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((c) => {
                  const badgeStatus = c.is_archived ? "archived" : c.status;
                  const fullWindow = `${new Date(c.start_time).toLocaleString()} → ${new Date(c.end_time).toLocaleString()}`;
                  return (
                    <tr key={c.id} className="border-t border-slate-800 hover:bg-slate-900/40">
                      <td className="px-3 py-3">
                        <input
                          type="checkbox"
                          checked={selected.has(c.id)}
                          onChange={() => toggleOne(c.id)}
                          aria-label={`Select ${c.title}`}
                          className="cursor-pointer"
                        />
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex flex-col gap-1">
                          <Link
                            href={`/contests/${c.id}`}
                            className="font-medium text-emerald-300 transition hover:underline"
                          >
                            {c.title}
                          </Link>
                          <div className="flex flex-wrap gap-1">
                            {(c.blocked_count ?? 0) > 0 && (
                              <span className="rounded bg-red-950/70 px-1.5 py-0.5 text-[10px] text-red-200">
                                {c.blocked_count} blocked
                              </span>
                            )}
                            {(c.clarifications_waiting ?? 0) > 0 && (
                              <span className="rounded bg-amber-950/70 px-1.5 py-0.5 text-[10px] text-amber-200">
                                {c.clarifications_waiting} waiting
                              </span>
                            )}
                            {c.results_held && (
                              <span className="rounded bg-slate-800 px-1.5 py-0.5 text-[10px] text-slate-300">
                                Results held
                              </span>
                            )}
                            {c.integrity_monitoring && (
                              <span className="rounded bg-slate-800 px-1.5 py-0.5 text-[10px] text-slate-400">
                                {c.integrity_strict ? "Strict" : "Integrity"}
                              </span>
                            )}
                            {!c.is_public && (
                              <span className="rounded bg-slate-800 px-1.5 py-0.5 text-[10px] text-slate-400">
                                Invite-only
                              </span>
                            )}
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-3 text-xs text-slate-400" title={fullWindow}>
                        {formatCompactWindow(c.start_time, c.end_time)}
                      </td>
                      <td className="px-4 py-3">
                        <span
                          className={`rounded-sm px-2 py-1 text-xs font-semibold uppercase ${statusTone(badgeStatus)}`}
                        >
                          {badgeStatus}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-slate-400">{c.problem_count ?? "—"}</td>
                      <td className="px-4 py-3 space-x-3 text-xs">
                        <button
                          type="button"
                          onClick={() => {
                            setPhase("setup");
                            setEditId(c.id);
                          }}
                          className="cursor-pointer text-emerald-300 hover:underline"
                        >
                          Manage
                        </button>
                        <Link
                          href={`/contests/${c.id}/scoreboard`}
                          className="text-slate-300 transition hover:text-white"
                        >
                          Scoreboard
                        </Link>
                        {!c.is_archived ? (
                          <button
                            type="button"
                            onClick={() => setConfirm({ type: "archive", contest: c })}
                            className="cursor-pointer text-slate-400 hover:text-white"
                          >
                            Archive
                          </button>
                        ) : (
                          <>
                            <button
                              type="button"
                              onClick={() =>
                                archiveMutation.mutate({ id: c.id, archived: false })
                              }
                              className="cursor-pointer text-slate-400 hover:text-white"
                            >
                              Unarchive
                            </button>
                            <button
                              type="button"
                              onClick={() => setConfirm({ type: "delete", contest: c })}
                              className="cursor-pointer text-red-300 hover:underline"
                            >
                              Delete
                            </button>
                          </>
                        )}
                        {c.status === "upcoming" && !c.is_archived && (
                          <button
                            type="button"
                            onClick={() => setConfirm({ type: "delete", contest: c })}
                            className="cursor-pointer text-red-300/80 hover:underline"
                          >
                            Delete
                          </button>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <Pagination
            page={page}
            pageSize={PAGE_SIZE}
            count={data?.count ?? 0}
            onPageChange={setPage}
          />
        </>
      )}

      <ConfirmDialog
        open={confirm?.type === "archive"}
        title="Archive contest?"
        body={
          confirm?.type === "archive"
            ? `“${confirm.contest.title}” will be hidden from students. You can unarchive or permanently delete it later.`
            : ""
        }
        confirmLabel="Archive"
        busy={archiveMutation.isPending}
        onCancel={() => setConfirm(null)}
        onConfirm={() => {
          if (confirm?.type === "archive") {
            archiveMutation.mutate({ id: confirm.contest.id, archived: true });
          }
        }}
      />
      <ConfirmDialog
        open={confirm?.type === "delete"}
        title="Permanently delete contest?"
        body={
          confirm?.type === "delete"
            ? `This removes “${confirm.contest.title}” and related contest data. This cannot be undone.`
            : ""
        }
        confirmLabel="Delete forever"
        busy={deleteMutation.isPending}
        onCancel={() => setConfirm(null)}
        onConfirm={() => {
          if (confirm?.type === "delete") {
            deleteMutation.mutate(confirm.contest.id);
          }
        }}
      />
      <ConfirmDialog
        open={confirm?.type === "bulk"}
        title={
          confirm?.type === "bulk"
            ? `${bulkLabels[confirm.action]} ${selectedIds.length} contest${selectedIds.length === 1 ? "" : "s"}?`
            : "Bulk action"
        }
        body={
          confirm?.type === "bulk"
            ? confirm.action === "archive"
              ? "Selected contests will be hidden from students. You can unarchive them later."
              : confirm.action === "set_public"
                ? "Selected contests will become visible for anyone to register."
                : "Selected contests will become invite-only."
            : ""
        }
        confirmLabel={
          confirm?.type === "bulk" ? bulkLabels[confirm.action] : "Confirm"
        }
        busy={bulkMutation.isPending}
        onCancel={() => setConfirm(null)}
        onConfirm={() => {
          if (confirm?.type === "bulk") {
            bulkMutation.mutate({ ids: selectedIds, action: confirm.action });
          }
        }}
      />
    </div>
  );
}
