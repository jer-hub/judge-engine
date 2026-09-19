"use client";

import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { formatApiErrorPayload } from "@/lib/admin";
import { ApiError, apiFetch } from "@/lib/api";
import type {
  AdminUser,
  ContestDetail,
  Paginated,
  ProblemListItem,
} from "@/lib/types";

type Props = {
  contestId: number;
  onClose: () => void;
};

type ProblemRow = {
  problem_id: number;
  letter: string;
  display_order: number;
  points: number;
};

const LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ".split("");

function withLetters(
  rows: Array<{ problem_id: number; points?: number }>,
): ProblemRow[] {
  return rows.map((r, i) => ({
    problem_id: r.problem_id,
    points: r.points ?? 100,
    letter: LETTERS[i] || `P${i + 1}`,
    display_order: i,
  }));
}

function toLocalInputValue(date: Date) {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

function formatDuration(startIso: string, endIso: string): string | null {
  const start = new Date(startIso);
  const end = new Date(endIso);
  if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime()) || end <= start) {
    return null;
  }
  const mins = Math.round((end.getTime() - start.getTime()) / 60_000);
  if (mins < 60) return `${mins} min`;
  const h = Math.floor(mins / 60);
  const m = mins % 60;
  return m ? `${h}h ${m}m` : `${h}h`;
}

function parseUsernameList(raw: string): string[] {
  const parts = raw
    .split(/[\s,;]+/)
    .map((s) => s.trim())
    .filter(Boolean);
  return Array.from(new Set(parts));
}

export function ContestEditor({ contestId, onClose }: Props) {
  const queryClient = useQueryClient();
  const rootRef = useRef<HTMLFormElement>(null);
  const closeAfterRef = useRef(false);
  const isDirtyRef = useRef(false);
  const savedMsgTimerRef = useRef<number | null>(null);
  const [pendingClose, setPendingClose] = useState(false);

  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [startTime, setStartTime] = useState("");
  const [endTime, setEndTime] = useState("");
  const [isPublic, setIsPublic] = useState(true);
  const [freeze, setFreeze] = useState(0);
  const [problems, setProblems] = useState<ProblemRow[]>([]);
  const [participantSet, setParticipantSet] = useState<string[]>([]);
  const [rosterSearch, setRosterSearch] = useState("");
  const [problemSearch, setProblemSearch] = useState("");
  const [pasteBuffer, setPasteBuffer] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [savedMsg, setSavedMsg] = useState<string | null>(null);

  const detail = useQuery({
    queryKey: ["admin", "contest", contestId],
    queryFn: () => apiFetch<ContestDetail>(`/contests/${contestId}/`),
  });

  const catalog = useQuery({
    queryKey: ["admin", "problems", "catalog"],
    queryFn: () =>
      apiFetch<Paginated<ProblemListItem>>("/problems/?page_size=100"),
  });

  const roster = useQuery({
    queryKey: ["admin", "users", "roster-picker"],
    queryFn: () => apiFetch<Paginated<AdminUser>>("/users/?page_size=100"),
  });

  function markDirty() {
    isDirtyRef.current = true;
  }

  function hydrateFrom(c: ContestDetail) {
    setTitle(c.title);
    setDescription(c.description || "");
    setStartTime(toLocalInputValue(new Date(c.start_time)));
    setEndTime(toLocalInputValue(new Date(c.end_time)));
    setIsPublic(c.is_public);
    setFreeze(c.freeze_scoreboard_minutes_before_end);
    setProblems(
      withLetters(
        c.problems.map((p) => ({
          problem_id: p.problem.id,
          points: p.points,
        })),
      ),
    );
    setParticipantSet((c.participants ?? []).map((p) => p.username));
    setError(null);
  }

  useEffect(() => {
    isDirtyRef.current = false;
    rootRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [contestId]);

  useEffect(() => {
    if (!detail.data) return;
    if (isDirtyRef.current) return;
    hydrateFrom(detail.data);
  }, [detail.data]);

  useEffect(() => {
    return () => {
      if (savedMsgTimerRef.current) window.clearTimeout(savedMsgTimerRef.current);
    };
  }, []);

  const rosterUsernames = useMemo(() => {
    const map = new Map<string, AdminUser>();
    for (const u of roster.data?.results ?? []) {
      map.set(u.username.toLowerCase(), u);
    }
    return map;
  }, [roster.data]);

  const unknownParticipants = useMemo(
    () =>
      participantSet.filter((name) => !rosterUsernames.has(name.toLowerCase())),
    [participantSet, rosterUsernames],
  );

  const saveMutation = useMutation({
    mutationFn: () =>
      apiFetch<ContestDetail>(`/contests/${contestId}/`, {
        method: "PATCH",
        body: JSON.stringify({
          title,
          description,
          start_time: new Date(startTime).toISOString(),
          end_time: new Date(endTime).toISOString(),
          is_public: isPublic,
          freeze_scoreboard_minutes_before_end: freeze,
          problems: withLetters(problems),
          participant_usernames: participantSet,
        }),
      }),
    onSuccess: (data) => {
      setError(null);
      isDirtyRef.current = false;
      hydrateFrom(data);
      queryClient.setQueryData(["admin", "contest", contestId], data);
      void queryClient.invalidateQueries({ queryKey: ["admin", "contests"] });
      void queryClient.invalidateQueries({ queryKey: ["contests"] });
      if (closeAfterRef.current) {
        onClose();
        return;
      }
      setSavedMsg("Saved.");
      if (savedMsgTimerRef.current) window.clearTimeout(savedMsgTimerRef.current);
      savedMsgTimerRef.current = window.setTimeout(() => {
        setSavedMsg(null);
        savedMsgTimerRef.current = null;
      }, 2500);
    },
    onError: (err: Error) => {
      setSavedMsg(null);
      setError(
        err instanceof ApiError
          ? formatApiErrorPayload(err.payload, err.message)
          : err.message,
      );
    },
  });

  function save(closeAfter: boolean) {
    closeAfterRef.current = closeAfter;
    setPendingClose(closeAfter);
    setError(null);
    if (new Date(endTime) <= new Date(startTime)) {
      setError("End time must be after start time.");
      return;
    }
    if (unknownParticipants.length > 0) {
      setError(
        `Unknown usernames: ${unknownParticipants.slice(0, 8).join(", ")}${
          unknownParticipants.length > 8 ? "…" : ""
        }. Remove them or create accounts first.`,
      );
      return;
    }
    saveMutation.mutate();
  }

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    save(false);
  }

  function addProblem(id: number) {
    if (!id || problems.some((p) => p.problem_id === id)) return;
    markDirty();
    setProblems((prev) => withLetters([...prev, { problem_id: id, points: 100 }]));
  }

  function removeProblem(idx: number) {
    markDirty();
    setProblems((prev) => withLetters(prev.filter((_, i) => i !== idx)));
  }

  function moveProblem(idx: number, dir: -1 | 1) {
    markDirty();
    setProblems((prev) => {
      const j = idx + dir;
      if (j < 0 || j >= prev.length) return prev;
      const next = [...prev];
      [next[idx], next[j]] = [next[j], next[idx]];
      return withLetters(next);
    });
  }

  function addAllPublished() {
    const published = (catalog.data?.results ?? []).filter(
      (p) => p.is_published && !problems.some((row) => row.problem_id === p.id),
    );
    if (published.length === 0) return;
    markDirty();
    setProblems((prev) =>
      withLetters([
        ...prev,
        ...published.map((p) => ({ problem_id: p.id, points: 100 })),
      ]),
    );
  }

  function applyDurationHours(hours: number) {
    markDirty();
    const start = startTime ? new Date(startTime) : new Date();
    if (Number.isNaN(start.getTime())) return;
    if (!startTime) setStartTime(toLocalInputValue(start));
    const end = new Date(start.getTime() + hours * 60 * 60 * 1000);
    setEndTime(toLocalInputValue(end));
  }

  function toggleParticipant(username: string) {
    markDirty();
    setParticipantSet((prev) => {
      const key = username.toLowerCase();
      const exists = prev.some((u) => u.toLowerCase() === key);
      if (exists) return prev.filter((u) => u.toLowerCase() !== key);
      const canonical =
        rosterUsernames.get(key)?.username ?? username.trim();
      return [...prev, canonical].sort((a, b) => a.localeCompare(b));
    });
  }

  function applyPaste() {
    const names = parseUsernameList(pasteBuffer);
    if (names.length === 0) return;
    markDirty();
    setParticipantSet((prev) => {
      const map = new Map(prev.map((u) => [u.toLowerCase(), u]));
      for (const name of names) {
        const key = name.toLowerCase();
        const canonical = rosterUsernames.get(key)?.username ?? name;
        map.set(key, canonical);
      }
      return Array.from(map.values()).sort((a, b) => a.localeCompare(b));
    });
    setPasteBuffer("");
  }

  const usedIds = new Set(problems.map((p) => p.problem_id));
  const available = (catalog.data?.results ?? []).filter((p) => !usedIds.has(p.id));
  const filteredAvailable = available.filter((p) => {
    const q = problemSearch.trim().toLowerCase();
    if (!q) return true;
    return p.title.toLowerCase().includes(q) || p.slug.toLowerCase().includes(q);
  });

  const filteredRoster = (roster.data?.results ?? []).filter((u) => {
    const q = rosterSearch.trim().toLowerCase();
    if (!q) return true;
    return (
      u.username.toLowerCase().includes(q) ||
      u.class_section.toLowerCase().includes(q) ||
      u.school_id.toLowerCase().includes(q)
    );
  });

  const durationLabel = formatDuration(startTime, endTime);
  const displayTitle = title.trim() || detail.data?.title || `Contest #${contestId}`;

  return (
    <form
      ref={rootRef}
      onSubmit={onSubmit}
      className="mt-3 space-y-4 rounded-xl border border-slate-700 bg-slate-950/70 p-4"
    >
      <div className="flex items-center justify-between gap-3">
        <h4 className="font-medium text-white">Edit · {displayTitle}</h4>
        <button
          type="button"
          onClick={onClose}
          className="cursor-pointer text-xs text-slate-400 hover:text-white"
        >
          Close
        </button>
      </div>

      {detail.isLoading && <p className="text-xs text-slate-500">Loading…</p>}
      {error && (
        <p role="alert" className="text-sm text-red-300">
          {error}
        </p>
      )}
      {savedMsg && (
        <p role="status" className="text-sm text-emerald-300">
          {savedMsg}
        </p>
      )}

      <div className="grid gap-3 sm:grid-cols-2">
        <label className="block text-sm sm:col-span-2">
          <span className="mb-1 block text-slate-400">Title</span>
          <input
            className="w-full rounded border border-slate-700 bg-slate-900 px-3 py-2"
            value={title}
            onChange={(e) => {
              markDirty();
              setTitle(e.target.value);
            }}
            required
          />
        </label>
        <label className="block text-sm sm:col-span-2">
          <span className="mb-1 block text-slate-400">Description</span>
          <textarea
            className="min-h-[72px] w-full rounded border border-slate-700 bg-slate-900 px-3 py-2 text-sm"
            value={description}
            onChange={(e) => {
              markDirty();
              setDescription(e.target.value);
            }}
          />
        </label>
        <label className="block text-sm">
          <span className="mb-1 block text-slate-400">Start</span>
          <input
            type="datetime-local"
            className="w-full rounded border border-slate-700 bg-slate-900 px-3 py-2"
            value={startTime}
            onChange={(e) => {
              markDirty();
              setStartTime(e.target.value);
            }}
            required
          />
        </label>
        <label className="block text-sm">
          <span className="mb-1 flex flex-wrap items-center justify-between gap-2 text-slate-400">
            <span>End</span>
            {durationLabel && (
              <span className="text-xs text-slate-500">Duration {durationLabel}</span>
            )}
          </span>
          <input
            type="datetime-local"
            className="w-full rounded border border-slate-700 bg-slate-900 px-3 py-2"
            value={endTime}
            onChange={(e) => {
              markDirty();
              setEndTime(e.target.value);
            }}
            required
          />
        </label>
        <div className="flex flex-wrap gap-2 sm:col-span-2">
          <span className="self-center text-xs text-slate-500">Length from start:</span>
          {[1, 2, 3].map((h) => (
            <button
              key={h}
              type="button"
              onClick={() => applyDurationHours(h)}
              aria-label={`Set contest length to ${h} hour${h === 1 ? "" : "s"} from start`}
              className="cursor-pointer rounded border border-slate-700 px-2.5 py-1 text-xs text-slate-300 hover:bg-slate-800"
            >
              {h}h
            </button>
          ))}
        </div>
        <label className="block text-sm">
          <span className="mb-1 block text-slate-400">Freeze (min before end)</span>
          <input
            type="number"
            min={0}
            className="w-full rounded border border-slate-700 bg-slate-900 px-3 py-2"
            value={freeze}
            onChange={(e) => {
              markDirty();
              setFreeze(Number(e.target.value));
            }}
          />
          <span className="mt-1 block text-xs text-slate-500">
            0 = never freeze. 60 = hide new solves in the last hour.
          </span>
        </label>
        <label className="flex flex-col gap-1 self-end text-sm">
          <span className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={isPublic}
              onChange={(e) => {
                markDirty();
                setIsPublic(e.target.checked);
              }}
              className="cursor-pointer"
            />
            <span>Public — anyone can see &amp; register</span>
          </span>
          <span className="text-xs text-slate-500">
            Uncheck for invite-only (use the participants list below).
          </span>
        </label>
      </div>

      <div>
        <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
          <h5 className="text-sm font-medium text-slate-200">
            Problem set{" "}
            <span className="font-normal text-slate-500">({problems.length})</span>
          </h5>
          <button
            type="button"
            onClick={addAllPublished}
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
          <p className="mb-3 rounded border border-dashed border-slate-700 px-3 py-4 text-center text-xs text-slate-500">
            No problems yet — pick from the list below.
          </p>
        ) : (
          <ul className="mb-3 space-y-2">
            {problems.map((row, idx) => {
              const meta = catalog.data?.results.find((p) => p.id === row.problem_id);
              return (
                <li
                  key={row.problem_id}
                  className="flex flex-wrap items-center gap-2 rounded border border-slate-800 px-3 py-2 text-xs"
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
                      onClick={() => moveProblem(idx, -1)}
                      className="cursor-pointer rounded border border-slate-700 px-2 py-0.5 text-slate-300 hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-40"
                    >
                      ↑
                    </button>
                    <button
                      type="button"
                      aria-label="Move down"
                      disabled={idx === problems.length - 1}
                      onClick={() => moveProblem(idx, 1)}
                      className="cursor-pointer rounded border border-slate-700 px-2 py-0.5 text-slate-300 hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-40"
                    >
                      ↓
                    </button>
                    <button
                      type="button"
                      onClick={() => removeProblem(idx)}
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
          className="mb-2 w-full rounded border border-slate-700 bg-slate-900 px-3 py-1.5 text-sm"
          placeholder="Search problems to add…"
          aria-label="Search problems to add"
          value={problemSearch}
          onChange={(e) => setProblemSearch(e.target.value)}
        />
        <ul
          aria-label="Problems available to add"
          className="max-h-40 space-y-1 overflow-y-auto rounded border border-slate-800 p-2"
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
                  onClick={() => addProblem(p.id)}
                  className="flex w-full cursor-pointer items-center justify-between gap-2 rounded px-2 py-1.5 text-left text-xs text-slate-300 hover:bg-slate-800"
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

      <div>
        <h5 className="mb-1 text-sm font-medium text-slate-200">
          Participants{" "}
          <span className="font-normal text-slate-500">
            ({participantSet.length} invited)
          </span>
        </h5>
        <p className="mb-2 text-xs text-slate-500">
          Pre-register students from the roster. They can also self-register if the contest is
          public.
        </p>

        {participantSet.length > 0 && (
          <div className="mb-2 flex flex-wrap gap-1.5">
            {participantSet.map((name) => {
              const unknown = !rosterUsernames.has(name.toLowerCase());
              return (
                <button
                  key={name}
                  type="button"
                  onClick={() => toggleParticipant(name)}
                  title="Click to remove"
                  aria-label={`Remove participant ${name}`}
                  className={`cursor-pointer rounded-full px-2.5 py-0.5 text-xs ${
                    unknown
                      ? "bg-amber-950/60 text-amber-200 ring-1 ring-amber-700"
                      : "bg-slate-800 text-slate-200 hover:bg-slate-700"
                  }`}
                >
                  {name} ×
                </button>
              );
            })}
          </div>
        )}

        {unknownParticipants.length > 0 && (
          <p className="mb-2 text-xs text-amber-300">
            Highlighted names are not in the roster — remove them before saving.
          </p>
        )}

        <input
          className="mb-2 w-full rounded border border-slate-700 bg-slate-900 px-3 py-1.5 text-sm"
          placeholder="Search roster (username, class, school id)…"
          aria-label="Search roster by username, class, or school id"
          value={rosterSearch}
          onChange={(e) => setRosterSearch(e.target.value)}
        />
        <ul
          aria-label="User roster"
          className="mb-2 max-h-44 space-y-1 overflow-y-auto rounded border border-slate-800 p-2"
        >
          {roster.isLoading && (
            <li className="px-2 py-1 text-xs text-slate-500">Loading roster…</li>
          )}
          {!roster.isLoading && filteredRoster.length === 0 && (
            <li className="px-2 py-1 text-xs text-slate-500">No users match.</li>
          )}
          {filteredRoster.map((u) => {
            const selected = participantSet.some(
              (n) => n.toLowerCase() === u.username.toLowerCase(),
            );
            return (
              <li key={u.id}>
                <button
                  type="button"
                  onClick={() => toggleParticipant(u.username)}
                  aria-pressed={selected}
                  aria-label={`${selected ? "Remove" : "Add"} ${u.username}`}
                  className={`flex w-full cursor-pointer items-center justify-between gap-2 rounded px-2 py-1.5 text-left text-xs hover:bg-slate-800 ${
                    selected ? "bg-emerald-950/40 text-emerald-200" : "text-slate-300"
                  }`}
                >
                  <span>
                    {u.username}
                    {u.class_section && (
                      <span className="ml-2 text-slate-500">{u.class_section}</span>
                    )}
                  </span>
                  <span className="text-slate-500">{selected ? "Added" : "Add"}</span>
                </button>
              </li>
            );
          })}
        </ul>

        <div className="flex flex-wrap gap-2">
          <input
            className="min-w-[200px] flex-1 rounded border border-slate-700 bg-slate-900 px-3 py-1.5 font-mono text-xs"
            placeholder="Paste usernames (comma or space separated)"
            aria-label="Paste usernames separated by comma or space"
            value={pasteBuffer}
            onChange={(e) => setPasteBuffer(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                applyPaste();
              }
            }}
          />
          <button
            type="button"
            onClick={applyPaste}
            className="cursor-pointer rounded border border-slate-700 px-3 py-1.5 text-xs text-slate-300 hover:bg-slate-800"
          >
            Add pasted
          </button>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <button
          type="submit"
          disabled={saveMutation.isPending}
          className="cursor-pointer rounded-lg bg-emerald-500 px-4 py-2 text-sm font-medium text-slate-950 hover:bg-emerald-400 disabled:opacity-60"
        >
          {saveMutation.isPending && !pendingClose ? "Saving…" : "Save"}
        </button>
        <button
          type="button"
          disabled={saveMutation.isPending}
          onClick={() => save(true)}
          className="cursor-pointer rounded-lg border border-slate-600 px-4 py-2 text-sm text-slate-200 hover:border-slate-400 disabled:opacity-60"
        >
          {saveMutation.isPending && pendingClose ? "Saving…" : "Save & close"}
        </button>
        <button
          type="button"
          onClick={onClose}
          className="cursor-pointer px-3 py-2 text-sm text-slate-400 hover:text-white"
        >
          Cancel
        </button>
      </div>
    </form>
  );
}
