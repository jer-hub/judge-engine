export type ContestProblemRow = {
  problem_id: number;
  letter: string;
  display_order: number;
  points: number;
};

const LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ".split("");

export function withLetters(
  rows: ReadonlyArray<{ problem_id: number; points?: number }>,
): ContestProblemRow[] {
  return rows.map((r, i) => ({
    problem_id: r.problem_id,
    points: r.points ?? 100,
    letter: LETTERS[i] || `P${i + 1}`,
    display_order: i,
  }));
}

export function moveProblemRow(
  rows: ReadonlyArray<ContestProblemRow>,
  idx: number,
  dir: -1 | 1,
): ContestProblemRow[] {
  const j = idx + dir;
  if (idx < 0 || idx >= rows.length || j < 0 || j >= rows.length) {
    return rows.map((r) => ({ ...r }));
  }
  const next = rows.map((r) => ({ ...r }));
  const tmp = next[idx];
  next[idx] = next[j];
  next[j] = tmp;
  return withLetters(next);
}

export function toLocalInputValue(date: Date): string {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

export function formatDuration(startIso: string, endIso: string): string | null {
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

export function parseUsernameList(raw: string): string[] {
  const parts = raw
    .split(/[\s,;]+/)
    .map((s) => s.trim())
    .filter(Boolean);
  return Array.from(new Set(parts));
}

/** Minimal roster diff as API add/remove lists so concurrent self-registrations are preserved. */
export function rosterChanges(
  saved: ReadonlyArray<string>,
  current: ReadonlyArray<string>,
): {
  participants_add?: string[];
  participants_remove?: string[];
} {
  const before = new Set(saved);
  const after = new Set(current);
  const add = current.filter((name) => !before.has(name));
  const remove = saved.filter((name) => !after.has(name));
  return {
    ...(add.length > 0 && { participants_add: add }),
    ...(remove.length > 0 && { participants_remove: remove }),
  };
}
