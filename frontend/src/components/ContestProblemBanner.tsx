"use client";

import Link from "next/link";

import { useClarifications } from "@/components/ContestClarifications";
import { Countdown } from "@/components/Countdown";
import { problemHref } from "@/lib/contest-context";
import type { ActiveContestRef, ContestDetail } from "@/lib/types";

type Props = {
  contest: ContestDetail;
  slug: string;
  /** Refetch the contest when the countdown crosses its start or end. */
  onPhaseChange: () => void;
};

/** Contest context above a problem opened from a contest: where it belongs,
 *  time left (the student's own, extensions included), and what happens
 *  once that time is up. */
export function ContestProblemBanner({ contest, slug, onPhaseChange }: Props) {
  const letter = contest.problems.find((p) => p.problem.slug === slug)?.letter;
  const over = contest.my_status === "past";
  const { data: clarifications } = useClarifications(contest.id, !over);
  // Newest public item for everyone, or for this problem.
  const latest = clarifications?.find(
    (c) => c.is_public && c.answered_at && (!c.problem_letter || c.problem_letter === letter),
  );

  return (
    <div
      className={`flex flex-wrap items-center justify-between gap-3 rounded-xl border p-3 text-sm ${
        over ? "border-slate-700 bg-slate-900/60" : "border-emerald-900/60 bg-emerald-950/20"
      }`}
    >
      <div className="space-y-1">
        <p className="text-slate-300">
          {letter && <span className="mr-2 font-mono text-emerald-300">{letter}</span>}
          <Link href={`/contests/${contest.id}`} className="font-medium text-white hover:underline">
            {contest.title}
          </Link>
          {" · "}
          <Link href={`/contests/${contest.id}/scoreboard`} className="text-emerald-300 hover:underline">
            Scoreboard
          </Link>
        </p>
        {latest && !over && (
          <p className="text-xs text-sky-200">
            <span className="font-semibold">
              {latest.is_announcement ? "Announcement" : "Clarification"}:
            </span>{" "}
            {latest.answer}{" "}
            <Link href={`/contests/${contest.id}`} className="text-sky-300 hover:underline">
              all
            </Link>
          </p>
        )}
        {over && (
          <p className="text-xs text-slate-400">
            Your time for this contest is over; submissions are closed.{" "}
            {contest.practice_after_end ? (
              <Link href={`/problems/${slug}`} className="text-emerald-300 hover:underline">
                Practice this problem
              </Link>
            ) : (
              "Its problems are not open for practice."
            )}
          </p>
        )}
      </div>
      {!over && (
        <Countdown
          startTime={contest.start_time}
          endTime={contest.my_end_time}
          serverTime={contest.server_time}
          onPhaseChange={onPhaseChange}
        />
      )}
    </div>
  );
}

/** Shown when a student opens an active contest problem without `?contest=<id>`. */
export function MissingContestBanner({
  slug,
  activeContests,
}: {
  slug: string;
  activeContests: ActiveContestRef[];
}) {
  if (activeContests.length === 0) return null;
  return (
    <div
      role="status"
      className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-amber-700/70 bg-amber-950/40 p-3 text-sm text-amber-100"
    >
      <div className="space-y-1">
        <p className="font-medium text-amber-50">
          This problem belongs to a live contest you&apos;re registered in.
        </p>
        <p className="text-xs text-amber-200/90">
          Practice submissions are disabled while the contest is running — switch to contest mode so your submission counts on the scoreboard.
        </p>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        {activeContests.map((c) => (
          <Link
            key={c.id}
            href={problemHref(slug, c.id)}
            className="rounded-sm bg-amber-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-amber-500"
          >
            Open in {c.title} ({c.letter})
          </Link>
        ))}
      </div>
    </div>
  );
}
