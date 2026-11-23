"use client";

import Link from "next/link";
import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { ConfirmDialog } from "@/components/ConfirmDialog";
import {
  bulkRejudge,
  describeRejudge,
  downloadSolutionsZip,
  downloadStandingsCsv,
  formatApiErrorPayload,
} from "@/lib/admin";
import { ApiError, apiFetch } from "@/lib/api";
import {
  type ContestProblemRow,
  formatDuration,
  moveProblemRow,
  parseUsernameList,
  rosterChanges,
  toLocalInputValue,
  withLetters,
} from "@/lib/contest-editor";
import { fetchAllPages } from "@/lib/pagination";
import type {
  AdminUser,
  ContestDetail,
  ContestEditorPhase,
  ProblemListItem,
} from "@/lib/types";

import { AdminClarifications } from "./AdminClarifications";
import { ContestExportsBar } from "./ContestExportsBar";
import { ContestParticipantsEditor } from "./ContestParticipantsEditor";
import { ContestProblemSetEditor } from "./ContestProblemSetEditor";
import { ContestResultsControls } from "./ContestResultsControls";
import { ContestSetupFields } from "./ContestSetupFields";
import { IntegrityPanel } from "./IntegrityPanel";
import { SimilarityPanel } from "./SimilarityPanel";

type Props = {
  contestId: number;
  onClose: () => void;
  phase: ContestEditorPhase;
  onPhaseChange: (phase: ContestEditorPhase) => void;
  onViewSubmissions?: () => void;
};

const PHASES: Array<{ id: ContestEditorPhase; label: string }> = [
  { id: "setup", label: "Setup" },
  { id: "live", label: "Live" },
  { id: "exports", label: "Exports" },
];

export function ContestEditor({
  contestId,
  onClose,
  phase,
  onPhaseChange,
  onViewSubmissions,
}: Props) {
  const queryClient = useQueryClient();
  const rootRef = useRef<HTMLFormElement>(null);
  const closeAfterRef = useRef(false);
  const isDirtyRef = useRef(false);
  const savedParticipantsRef = useRef<string[]>([]);
  const savedMsgTimerRef = useRef<number | null>(null);
  const [pendingClose, setPendingClose] = useState(false);
  const [discardOpen, setDiscardOpen] = useState(false);

  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [startTime, setStartTime] = useState("");
  const [endTime, setEndTime] = useState("");
  const [isPublic, setIsPublic] = useState(true);
  const [freeze, setFreeze] = useState(0);
  const [holdResults, setHoldResults] = useState(false);
  const [practiceAfterEnd, setPracticeAfterEnd] = useState(false);
  const [integrityMonitoring, setIntegrityMonitoring] = useState(true);
  const [integrityStrict, setIntegrityStrict] = useState(false);
  const [problems, setProblems] = useState<ContestProblemRow[]>([]);
  const [participantSet, setParticipantSet] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [savedMsg, setSavedMsg] = useState<string | null>(null);
  const [exportSection, setExportSection] = useState("");
  const [exporting, setExporting] = useState(false);
  const [exportingSolutions, setExportingSolutions] = useState(false);
  const [confirmRejudge, setConfirmRejudge] = useState(false);

  const detail = useQuery({
    queryKey: ["admin", "contest", contestId],
    queryFn: () => apiFetch<ContestDetail>(`/contests/${contestId}/`),
  });

  const catalog = useQuery({
    queryKey: ["admin", "problems", "catalog"],
    queryFn: () => fetchAllPages<ProblemListItem>("/problems/"),
  });

  const roster = useQuery({
    queryKey: ["admin", "users", "roster-picker"],
    queryFn: () => fetchAllPages<AdminUser>("/users/"),
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
    setHoldResults(c.hold_results_until_revealed);
    setPracticeAfterEnd(c.practice_after_end);
    setIntegrityMonitoring(c.integrity_monitoring !== false);
    setIntegrityStrict(!!c.integrity_strict);
    setProblems(
      withLetters(
        c.problems.map((p) => ({
          problem_id: p.problem.id,
          points: p.points,
        })),
      ),
    );
    const saved = (c.participants ?? []).map((p) => p.username);
    savedParticipantsRef.current = saved;
    setParticipantSet(saved);
    setError(null);
  }

  useEffect(() => {
    isDirtyRef.current = false;
    rootRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [contestId]);

  useEffect(() => {
    if (!detail.data || isDirtyRef.current) return;
    hydrateFrom(detail.data);
  }, [detail.data]);

  useEffect(() => {
    return () => {
      if (savedMsgTimerRef.current) window.clearTimeout(savedMsgTimerRef.current);
    };
  }, []);

  useEffect(() => {
    const onBeforeUnload = (e: BeforeUnloadEvent) => {
      if (!isDirtyRef.current) return;
      e.preventDefault();
      e.returnValue = "";
    };
    window.addEventListener("beforeunload", onBeforeUnload);
    return () => window.removeEventListener("beforeunload", onBeforeUnload);
  }, []);

  const rosterUsernames = useMemo(() => {
    const map = new Map<string, AdminUser>();
    for (const u of roster.data?.results ?? []) {
      map.set(u.username.toLowerCase(), u);
    }
    return map;
  }, [roster.data]);

  const participantSections = useMemo(() => {
    const sections = new Set<string>();
    for (const p of detail.data?.participants ?? []) {
      const section = rosterUsernames.get(p.username.toLowerCase())?.class_section?.trim();
      if (section) sections.add(section);
    }
    return [...sections].sort((a, b) => a.localeCompare(b));
  }, [detail.data, rosterUsernames]);

  const unknownParticipants = useMemo(() => {
    if (!roster.isSuccess) return [];
    const saved = new Set(savedParticipantsRef.current);
    return participantSet.filter(
      (name) => !saved.has(name) && !rosterUsernames.has(name.toLowerCase()),
    );
  }, [participantSet, rosterUsernames, roster.isSuccess]);

  async function exportStandings() {
    setExporting(true);
    setError(null);
    try {
      await downloadStandingsCsv(contestId, exportSection || undefined);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setExporting(false);
    }
  }

  async function exportSolutions() {
    setExportingSolutions(true);
    setError(null);
    try {
      await downloadSolutionsZip({ contest: contestId, section: exportSection || undefined });
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setExportingSolutions(false);
    }
  }

  const rejudgeMutation = useMutation({
    mutationFn: () => bulkRejudge({ contest: contestId }),
    onSuccess: (result) => {
      setConfirmRejudge(false);
      setError(null);
      setSavedMsg(describeRejudge(result));
      void queryClient.invalidateQueries({ queryKey: ["scoreboard", String(contestId)] });
      void queryClient.invalidateQueries({ queryKey: ["admin", "submissions"] });
    },
    onError: (err: Error) => {
      setConfirmRejudge(false);
      setError(
        err instanceof ApiError ? formatApiErrorPayload(err.payload, err.message) : err.message,
      );
    },
  });

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
          hold_results_until_revealed: holdResults,
          practice_after_end: practiceAfterEnd,
          integrity_monitoring: integrityMonitoring,
          integrity_strict: integrityStrict,
          problems: withLetters(problems),
          ...rosterChanges(savedParticipantsRef.current, participantSet),
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
    setProblems((prev) => moveProblemRow(prev, idx, dir));
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
      const canonical = rosterUsernames.get(key)?.username ?? username.trim();
      return [...prev, canonical].sort((a, b) => a.localeCompare(b));
    });
  }

  function applyPaste(raw: string) {
    const names = parseUsernameList(raw);
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
  }

  function requestClose() {
    if (isDirtyRef.current) {
      setDiscardOpen(true);
      return;
    }
    onClose();
  }

  const durationLabel = formatDuration(startTime, endTime);
  const displayTitle = title.trim() || detail.data?.title || `Contest #${contestId}`;
  const statusLabel = detail.data?.status ?? "…";
  const checklistIncomplete = problems.length === 0 || participantSet.length === 0;

  return (
    <form
      ref={rootRef}
      onSubmit={onSubmit}
      className="space-y-4 rounded-xl border border-slate-700 bg-slate-950/70 p-4"
    >
      <div className="sticky top-0 z-10 -mx-4 -mt-4 space-y-3 border-b border-slate-800 bg-slate-950/95 px-4 py-3 backdrop-blur-sm">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap items-center gap-3">
            <button
              type="button"
              onClick={requestClose}
              className="cursor-pointer text-xs text-slate-400 hover:text-white"
            >
              ← Contests
            </button>
            <h4 className="font-medium text-white">{displayTitle}</h4>
            <span
              className={`rounded-sm px-2 py-0.5 text-[10px] font-semibold uppercase ${
                statusLabel === "active"
                  ? "bg-emerald-900/50 text-emerald-300"
                  : statusLabel === "upcoming"
                    ? "bg-sky-900/50 text-sky-200"
                    : "bg-slate-800 text-slate-400"
              }`}
            >
              {statusLabel}
            </span>
          </div>
          <div className="flex flex-wrap items-center gap-3 text-xs">
            <Link
              href={`/contests/${contestId}/scoreboard`}
              className="text-slate-300 hover:text-white"
            >
              Scoreboard
            </Link>
            {onViewSubmissions && (
              <button
                type="button"
                onClick={onViewSubmissions}
                className="cursor-pointer text-emerald-300 hover:underline"
              >
                View submissions
              </button>
            )}
            <button
              type="button"
              onClick={requestClose}
              className="cursor-pointer text-slate-400 hover:text-white"
            >
              Close
            </button>
          </div>
        </div>
        <div
          role="tablist"
          aria-label="Contest workspace"
          className="flex flex-wrap gap-1"
        >
          {PHASES.map((p) => (
            <button
              key={p.id}
              type="button"
              role="tab"
              aria-selected={phase === p.id}
              onClick={() => onPhaseChange(p.id)}
              className={`cursor-pointer rounded-md px-3 py-1.5 text-xs font-medium transition ${
                phase === p.id
                  ? "bg-slate-800 text-white"
                  : "text-slate-400 hover:bg-slate-900 hover:text-slate-200"
              }`}
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>

      <ConfirmDialog
        open={confirmRejudge}
        title="Rejudge this contest?"
        body={`Re-judge every finished submission in “${displayTitle}” against the current test cases. Verdicts and the scoreboard may change.`}
        confirmLabel="Rejudge"
        busy={rejudgeMutation.isPending}
        onCancel={() => setConfirmRejudge(false)}
        onConfirm={() => rejudgeMutation.mutate()}
      />
      <ConfirmDialog
        open={discardOpen}
        title="Discard unsaved changes?"
        body="You have unsaved Setup changes. Leave without saving?"
        confirmLabel="Discard"
        onCancel={() => setDiscardOpen(false)}
        onConfirm={() => {
          setDiscardOpen(false);
          isDirtyRef.current = false;
          onClose();
        }}
      />

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

      {phase === "setup" && checklistIncomplete && (
        <div className="rounded-sm border border-amber-900/50 bg-amber-950/20 px-3 py-2 text-xs text-amber-100">
          Setup checklist:{" "}
          {problems.length === 0 ? "attach at least one problem" : null}
          {problems.length === 0 && participantSet.length === 0 ? "; " : null}
          {participantSet.length === 0 ? "invite at least one participant" : null}.
        </div>
      )}

      {phase === "live" && (
        <p className="text-xs text-slate-500">
          Live actions apply immediately — they are not part of Save.
        </p>
      )}

      {phase === "exports" && (
        <ContestExportsBar
          exportSection={exportSection}
          onExportSectionChange={setExportSection}
          participantSections={participantSections}
          exporting={exporting}
          onExportStandings={() => void exportStandings()}
          exportingSolutions={exportingSolutions}
          onExportSolutions={() => void exportSolutions()}
          rejudgePending={rejudgeMutation.isPending}
          onRequestRejudge={() => setConfirmRejudge(true)}
        />
      )}

      {phase === "setup" && (
        <>
          <ContestSetupFields
            title={title}
            onTitleChange={(v) => {
              markDirty();
              setTitle(v);
            }}
            description={description}
            onDescriptionChange={(v) => {
              markDirty();
              setDescription(v);
            }}
            startTime={startTime}
            onStartTimeChange={(v) => {
              markDirty();
              setStartTime(v);
            }}
            endTime={endTime}
            onEndTimeChange={(v) => {
              markDirty();
              setEndTime(v);
            }}
            durationLabel={durationLabel}
            onApplyDurationHours={applyDurationHours}
            freeze={freeze}
            onFreezeChange={(v) => {
              markDirty();
              setFreeze(v);
            }}
            isPublic={isPublic}
            onIsPublicChange={(v) => {
              markDirty();
              setIsPublic(v);
            }}
            holdResults={holdResults}
            onHoldResultsChange={(v) => {
              markDirty();
              setHoldResults(v);
            }}
            practiceAfterEnd={practiceAfterEnd}
            onPracticeAfterEndChange={(v) => {
              markDirty();
              setPracticeAfterEnd(v);
            }}
            integrityMonitoring={integrityMonitoring}
            onIntegrityMonitoringChange={(v) => {
              markDirty();
              setIntegrityMonitoring(v);
            }}
            integrityStrict={integrityStrict}
            onIntegrityStrictChange={(v) => {
              markDirty();
              setIntegrityStrict(v);
            }}
          />

          <ContestProblemSetEditor
            problems={problems}
            catalogProblems={catalog.data?.results ?? []}
            onAddProblem={addProblem}
            onRemoveProblem={removeProblem}
            onMoveProblem={moveProblem}
            onAddAllPublished={addAllPublished}
          />

          <ContestParticipantsEditor
            participantSet={participantSet}
            unknownParticipants={unknownParticipants}
            rosterUsers={roster.data?.results ?? []}
            rosterLoading={roster.isLoading}
            onToggleParticipant={toggleParticipant}
            onApplyPaste={applyPaste}
          />

          <div className="sticky bottom-0 z-10 -mx-4 -mb-4 flex flex-wrap items-center gap-2 border-t border-slate-800 bg-slate-950/95 px-4 py-3 backdrop-blur-sm">
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
              onClick={requestClose}
              className="cursor-pointer px-3 py-2 text-sm text-slate-400 hover:text-white"
            >
              Cancel
            </button>
          </div>
        </>
      )}

      {phase === "live" && detail.data && (
        <div className="space-y-3">
          <ContestResultsControls contest={detail.data} />
          <AdminClarifications contestId={detail.data.id} />
          <IntegrityPanel contestId={detail.data.id} />
          <SimilarityPanel contestId={detail.data.id} />
        </div>
      )}
    </form>
  );
}
