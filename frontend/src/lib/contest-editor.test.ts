import { describe, expect, it } from "vitest";

import {
  formatDuration,
  moveProblemRow,
  parseUsernameList,
  rosterChanges,
  withLetters,
} from "@/lib/contest-editor";

describe("contest-editor helpers", () => {
  it("assigns sequential problem letters and display_order immutably", () => {
    const rows = withLetters([{ problem_id: 10 }, { problem_id: 20, points: 250 }]);
    expect(rows).toEqual([
      { problem_id: 10, points: 100, letter: "A", display_order: 0 },
      { problem_id: 20, points: 250, letter: "B", display_order: 1 },
    ]);
  });

  it("reorders problem rows without mutating original array and re-letters", () => {
    const initial = withLetters([{ problem_id: 1 }, { problem_id: 2 }, { problem_id: 3 }]);
    const snapshot = [...initial];
    const moved = moveProblemRow(initial, 1, -1);
    expect(initial).toEqual(snapshot);
    expect(moved.map((r) => [r.letter, r.problem_id])).toEqual([
      ["A", 2],
      ["B", 1],
      ["C", 3],
    ]);
    // Out-of-bounds move returns equivalent list
    expect(moveProblemRow(initial, 0, -1)).toEqual(initial);
  });

  it("parses and deduplicates pasted usernames across commas, semicolons, and whitespace", () => {
    expect(parseUsernameList(" alice, bob ; carol\nalice  ")).toEqual(["alice", "bob", "carol"]);
  });

  it("computes minimal rosterChanges diff against saved participants", () => {
    expect(rosterChanges(["alice", "bob"], ["bob", "carol"])).toEqual({
      participants_add: ["carol"],
      participants_remove: ["alice"],
    });
    expect(rosterChanges(["alice"], ["alice"])).toEqual({});
  });

  it("formats contest durations cleanly and returns null when invalid", () => {
    expect(formatDuration("2026-11-23T09:00", "2026-11-23T11:30")).toBe("2h 30m");
    expect(formatDuration("2026-11-23T09:00", "2026-11-23T09:45")).toBe("45 min");
    expect(formatDuration("2026-11-23T11:00", "2026-11-23T09:00")).toBeNull();
  });
});
