import type { ReactNode } from "react";

type Metric = {
  label: string;
  value: string | number;
  hint: string;
  icon: ReactNode;
  tone?: "default" | "accent" | "warn";
};

const toneClass = {
  default: "text-slate-200",
  accent: "text-emerald-300",
  warn: "text-amber-200",
} as const;

export function MetricCards({ metrics }: { metrics: Metric[] }) {
  return (
    <div className="admin-stagger grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
      {metrics.map((m) => (
        <div
          key={m.label}
          className="rounded-xl border border-[var(--admin-border)] bg-[var(--admin-card)] p-4 shadow-[inset_0_1px_0_rgba(255,255,255,0.04)] backdrop-blur-md"
        >
          <div className="mb-3 flex items-center justify-between">
            <span className="text-xs font-medium uppercase tracking-wide text-slate-400">
              {m.label}
            </span>
            <span className="text-slate-500" aria-hidden="true">
              {m.icon}
            </span>
          </div>
          <p className={`font-mono text-3xl font-semibold tabular-nums ${toneClass[m.tone ?? "default"]}`}>
            {m.value}
          </p>
          <p className="mt-1 text-xs text-slate-500">{m.hint}</p>
        </div>
      ))}
    </div>
  );
}
