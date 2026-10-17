"use client";

import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { Suspense, useCallback, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";

import { djangoAdminUrl } from "@/lib/admin";
import { apiFetch } from "@/lib/api";
import type {
  ContestEditorPhase,
  ContestListItem,
  Paginated,
  ProblemListItem,
  Submission,
  User,
} from "@/lib/types";

import { AccountsPanel } from "./_components/AccountsPanel";
import { ActivityPanel } from "./_components/ActivityPanel";
import { ContestsPanel } from "./_components/ContestsPanel";
import { JudgeHealthCard } from "./_components/JudgeHealthCard";
import { MetricCards } from "./_components/MetricCards";
import { ProblemsPanel } from "./_components/ProblemsPanel";
import { SubmissionsPanel } from "./_components/SubmissionsPanel";
import {
  BookIcon,
  ChartBarIcon,
  GearIcon,
  TrophyIcon,
  UsersIcon,
} from "./_components/icons";

type TabId = "problems" | "contests" | "submissions" | "accounts" | "activity";
type ContestStatusFilter = "all" | "upcoming" | "active" | "past" | "archived";

const TABS: Array<{ id: TabId; label: string }> = [
  { id: "problems", label: "Problems" },
  { id: "contests", label: "Contests" },
  { id: "submissions", label: "Submissions" },
  { id: "accounts", label: "Accounts" },
  { id: "activity", label: "Activity" },
];

const TAB_IDS = new Set<string>(TABS.map((t) => t.id));
const PHASES = new Set<string>(["setup", "live", "exports"]);
const STATUS_FILTERS = new Set<string>([
  "all",
  "upcoming",
  "active",
  "past",
  "archived",
]);

function parseTab(raw: string | null): TabId {
  if (raw && TAB_IDS.has(raw)) return raw as TabId;
  return "problems";
}

function parsePhase(raw: string | null): ContestEditorPhase {
  if (raw && PHASES.has(raw)) return raw as ContestEditorPhase;
  return "setup";
}

function parseStatus(raw: string | null): ContestStatusFilter {
  if (raw && STATUS_FILTERS.has(raw)) return raw as ContestStatusFilter;
  return "all";
}

function AdminPageInner() {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const tab = parseTab(searchParams.get("tab"));
  // Contests Manage uses `contest`+`phase`; Submissions filter uses `sub_contest`.
  const contestRaw = searchParams.get("contest");
  const contestId =
    tab === "contests" && contestRaw && /^\d+$/.test(contestRaw)
      ? Number(contestRaw)
      : null;
  const phase = parsePhase(searchParams.get("phase"));
  const contestStatus = parseStatus(searchParams.get("status"));
  const subContestRaw = searchParams.get("sub_contest");
  const submissionsContestId =
    tab === "submissions" && subContestRaw && /^\d+$/.test(subContestRaw)
      ? Number(subContestRaw)
      : null;

  const replaceParams = useCallback(
    (patch: Record<string, string | null>) => {
      const next = new URLSearchParams(searchParams.toString());
      for (const [key, value] of Object.entries(patch)) {
        if (value === null || value === "") next.delete(key);
        else next.set(key, value);
      }
      const qs = next.toString();
      router.replace(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
    },
    [pathname, router, searchParams],
  );

  const setTab = useCallback(
    (next: TabId) => {
      if (next === "contests") {
        // Keep list/status; do not open an editor from a submissions filter id.
        replaceParams({
          tab: "contests",
          contest: null,
          phase: null,
          sub_contest: null,
          status: contestStatus !== "all" ? contestStatus : null,
        });
        return;
      }
      if (next === "submissions") {
        replaceParams({
          tab: "submissions",
          contest: null,
          phase: null,
          status: null,
          // Preserve existing submissions filter if already set in the URL.
          sub_contest: searchParams.get("sub_contest"),
        });
        return;
      }
      replaceParams({
        tab: next === "problems" ? null : next,
        contest: null,
        phase: null,
        status: null,
        sub_contest: null,
      });
    },
    [contestStatus, replaceParams, searchParams],
  );

  const me = useQuery({
    queryKey: ["me"],
    queryFn: () => apiFetch<User>("/auth/me/"),
    retry: false,
  });

  const problems = useQuery({
    queryKey: ["admin", "problems", "metrics"],
    queryFn: () =>
      apiFetch<Paginated<ProblemListItem>>("/problems/?page_size=1"),
    enabled: !!me.data?.is_platform_admin,
  });

  const publishedProblems = useQuery({
    queryKey: ["admin", "problems", "metrics", "published"],
    queryFn: () =>
      apiFetch<Paginated<ProblemListItem>>(
        "/problems/?is_published=true&page_size=1",
      ),
    enabled: !!me.data?.is_platform_admin,
  });

  const contests = useQuery({
    queryKey: ["admin", "contests", "metrics"],
    queryFn: () =>
      apiFetch<Paginated<ContestListItem>>("/contests/?page_size=100"),
    enabled: !!me.data?.is_platform_admin,
  });

  const submissions = useQuery({
    queryKey: ["admin", "submissions", { page_size: 20 }],
    queryFn: () =>
      apiFetch<Paginated<Submission>>("/submissions/?page_size=20"),
    enabled: !!me.data?.is_platform_admin,
  });

  const metrics = useMemo(() => {
    const contestRows = contests.data?.results ?? [];
    const live = contestRows.filter(
      (c) => c.status === "active" && !c.is_archived,
    ).length;
    const pending = (submissions.data?.results ?? []).filter((s) =>
      ["Pending", "Judging"].includes(s.status),
    ).length;

    return [
      {
        label: "Problems",
        value: problems.data?.count ?? "—",
        hint: `${publishedProblems.data?.count ?? "—"} published`,
        icon: <BookIcon className="h-4 w-4" />,
        onClick: () => setTab("problems"),
      },
      {
        label: "Contests",
        value: contests.data?.count ?? "—",
        hint: `${live} live now`,
        icon: <TrophyIcon className="h-4 w-4" />,
        tone: live > 0 ? ("accent" as const) : ("default" as const),
        onClick: () => {
          replaceParams({
            tab: "contests",
            status: "active",
            contest: null,
            phase: null,
          });
        },
      },
      {
        label: "Submissions",
        value: submissions.data?.count ?? "—",
        hint: pending > 0 ? `${pending} in queue` : "Queue clear",
        icon: <ChartBarIcon className="h-4 w-4" />,
        tone: pending > 0 ? ("warn" as const) : ("default" as const),
        onClick: () => setTab("submissions"),
      },
      {
        label: "Operator",
        value: me.data?.username ?? "—",
        hint: me.data?.role ?? "admin",
        icon: <UsersIcon className="h-4 w-4" />,
        tone: "accent" as const,
        onClick: () => setTab("accounts"),
      },
    ];
  }, [
    problems.data,
    publishedProblems.data,
    contests.data,
    submissions.data,
    me.data,
    replaceParams,
    setTab,
  ]);

  if (me.isLoading) {
    return <AdminSkeleton />;
  }

  if (me.error || !me.data) {
    return (
      <AccessCard
        title="Sign in required"
        body="Platform admin management needs an authenticated session."
        actionHref="/login?next=/admin"
        actionLabel="Log in"
      />
    );
  }

  if (!me.data.is_platform_admin) {
    return (
      <AccessCard
        title="Admins only"
        body="Your account does not have platform admin access. Ask an operator to set role=admin."
        actionHref="/problems"
        actionLabel="Back to problems"
      />
    );
  }

  return (
    <div className="space-y-5">
      <div className="sticky top-0 z-20 -mx-1 space-y-4 bg-[color-mix(in_oklab,var(--background)_92%,transparent)] px-1 py-3 backdrop-blur-md">
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="text-xs font-medium uppercase tracking-[0.16em] text-emerald-400/90">
              Operations
            </p>
            <h1 className="mt-1 text-2xl font-semibold tracking-tight text-white sm:text-3xl">
              Admin
            </h1>
            <p className="mt-1 max-w-xl text-sm text-slate-400">
              Problems, contests, queue, and accounts.
            </p>
          </div>
          <a
            href={djangoAdminUrl()}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex cursor-pointer items-center gap-2 rounded-lg border border-slate-700 bg-slate-900/60 px-3 py-2 text-sm text-slate-300 transition hover:border-slate-500 hover:bg-slate-800"
          >
            <GearIcon className="h-4 w-4" aria-hidden="true" />
            Django Admin
          </a>
        </div>
        <MetricCards metrics={metrics} />
        <JudgeHealthCard />
      </div>

      <div>
        <div
          role="tablist"
          aria-label="Admin sections"
          className="flex flex-wrap gap-1 rounded-xl border border-slate-800 bg-slate-950/60 p-1"
        >
          {TABS.map((t) => {
            const selected = tab === t.id;
            return (
              <button
                key={t.id}
                type="button"
                role="tab"
                aria-selected={selected}
                id={`admin-tab-${t.id}`}
                aria-controls={`admin-panel-${t.id}`}
                onClick={() => setTab(t.id)}
                className={`cursor-pointer rounded-lg px-3 py-2 text-sm font-medium transition ${
                  selected
                    ? "bg-slate-800 text-white shadow-xs"
                    : "text-slate-400 hover:bg-slate-900 hover:text-slate-200"
                }`}
              >
                {t.label}
              </button>
            );
          })}
        </div>

        <div
          role="tabpanel"
          id={`admin-panel-${tab}`}
          aria-labelledby={`admin-tab-${tab}`}
          className="mt-4 rounded-xl border border-slate-800 bg-slate-950/40 p-4 backdrop-blur-xs"
        >
          {tab === "problems" && <ProblemsPanel />}
          {tab === "contests" && (
            <ContestsPanel
              statusFilter={contestStatus}
              contestId={contestId}
              phase={phase}
              onStatusFilterChange={(status) =>
                replaceParams({
                  tab: "contests",
                  status: status === "all" ? null : status,
                })
              }
              onContestChange={(id) =>
                replaceParams({
                  tab: "contests",
                  contest: id != null ? String(id) : null,
                  phase: id != null ? phase : null,
                  sub_contest: null,
                })
              }
              onPhaseChange={(nextPhase) =>
                replaceParams({
                  tab: "contests",
                  contest: contestId != null ? String(contestId) : null,
                  phase: nextPhase,
                })
              }
              onViewSubmissions={(id) =>
                replaceParams({
                  tab: "submissions",
                  sub_contest: String(id),
                  contest: null,
                  phase: null,
                  status: null,
                })
              }
            />
          )}
          {tab === "submissions" && (
            <SubmissionsPanel
              contestId={submissionsContestId}
              onContestFilterChange={(id) =>
                replaceParams({
                  tab: "submissions",
                  sub_contest: id != null ? String(id) : null,
                  contest: null,
                  phase: null,
                  status: null,
                })
              }
            />
          )}
          {tab === "accounts" && <AccountsPanel />}
          {tab === "activity" && <ActivityPanel />}
        </div>
      </div>
    </div>
  );
}

export default function AdminPage() {
  return (
    <Suspense fallback={<AdminSkeleton />}>
      <AdminPageInner />
    </Suspense>
  );
}

function AccessCard({
  title,
  body,
  actionHref,
  actionLabel,
}: {
  title: string;
  body: string;
  actionHref: string;
  actionLabel: string;
}) {
  return (
    <div className="mx-auto max-w-lg rounded-xl border border-slate-800 bg-slate-950/60 p-8 text-center backdrop-blur-sm">
      <h1 className="text-2xl font-semibold text-white">{title}</h1>
      <p className="mt-2 text-sm text-slate-400">{body}</p>
      <Link
        href={actionHref}
        className="mt-6 inline-flex cursor-pointer rounded-lg bg-emerald-500 px-4 py-2 text-sm font-medium text-slate-950 transition hover:bg-emerald-400"
      >
        {actionLabel}
      </Link>
    </div>
  );
}

function AdminSkeleton() {
  return (
    <div className="space-y-6" aria-busy="true" aria-label="Loading admin">
      <div className="h-16 max-w-md animate-pulse rounded-lg bg-slate-900" />
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="h-28 animate-pulse rounded-xl bg-slate-900" />
        ))}
      </div>
      <div className="h-64 animate-pulse rounded-xl bg-slate-900" />
    </div>
  );
}
