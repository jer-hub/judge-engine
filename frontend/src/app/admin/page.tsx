"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { djangoAdminUrl } from "@/lib/admin";
import { apiFetch } from "@/lib/api";
import type {
  ContestListItem,
  Paginated,
  ProblemListItem,
  Submission,
  User,
} from "@/lib/types";

import { AccountsPanel } from "./_components/AccountsPanel";
import { ContestsPanel } from "./_components/ContestsPanel";
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

type TabId = "problems" | "contests" | "submissions" | "accounts";

const TABS: Array<{ id: TabId; label: string }> = [
  { id: "problems", label: "Problems" },
  { id: "contests", label: "Contests" },
  { id: "submissions", label: "Submissions" },
  { id: "accounts", label: "Accounts" },
];

export default function AdminPage() {
  const [tab, setTab] = useState<TabId>("problems");

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
    queryKey: ["admin", "contests"],
    queryFn: () => apiFetch<Paginated<ContestListItem>>("/contests/?page_size=100"),
    enabled: !!me.data?.is_platform_admin,
  });

  const submissions = useQuery({
    queryKey: ["admin", "submissions"],
    queryFn: () => apiFetch<Paginated<Submission>>("/submissions/?page_size=20"),
    enabled: !!me.data?.is_platform_admin,
  });

  const metrics = useMemo(() => {
    const contestRows = contests.data?.results ?? [];
    const live = contestRows.filter((c) => c.status === "active").length;
    const pending = (submissions.data?.results ?? []).filter((s) =>
      ["Pending", "Judging"].includes(s.status),
    ).length;

    return [
      {
        label: "Problems",
        value: problems.data?.count ?? "—",
        hint: `${publishedProblems.data?.count ?? "—"} published`,
        icon: <BookIcon className="h-4 w-4" />,
      },
      {
        label: "Contests",
        value: contests.data?.count ?? "—",
        hint: `${live} live now`,
        icon: <TrophyIcon className="h-4 w-4" />,
        tone: live > 0 ? ("accent" as const) : ("default" as const),
      },
      {
        label: "Submissions",
        value: submissions.data?.count ?? "—",
        hint: pending > 0 ? `${pending} in queue` : "Queue clear",
        icon: <ChartBarIcon className="h-4 w-4" />,
        tone: pending > 0 ? ("warn" as const) : ("default" as const),
      },
      {
        label: "Operator",
        value: me.data?.username ?? "—",
        hint: me.data?.role ?? "admin",
        icon: <UsersIcon className="h-4 w-4" />,
        tone: "accent" as const,
      },
    ];
  }, [problems.data, publishedProblems.data, contests.data, submissions.data, me.data]);

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
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-xs font-medium uppercase tracking-[0.16em] text-emerald-400/90">
            Operations
          </p>
          <h1 className="mt-1 text-3xl font-semibold tracking-tight text-white">
            Admin management
          </h1>
          <p className="mt-1 max-w-xl text-sm text-slate-400">
            Publish problems, schedule contests, watch the judge queue, and jump to Django for
            accounts and test cases.
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
                    ? "bg-slate-800 text-white shadow-sm"
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
          className="mt-4 rounded-xl border border-slate-800 bg-slate-950/40 p-4 backdrop-blur-sm"
        >
          {tab === "problems" && <ProblemsPanel />}
          {tab === "contests" && <ContestsPanel />}
          {tab === "submissions" && <SubmissionsPanel />}
          {tab === "accounts" && <AccountsPanel />}
        </div>
      </div>
    </div>
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
    <div className="mx-auto max-w-lg rounded-xl border border-slate-800 bg-slate-950/60 p-8 text-center backdrop-blur">
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
