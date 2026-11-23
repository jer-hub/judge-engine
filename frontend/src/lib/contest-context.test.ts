import { describe, expect, it } from "vitest";

import { missingContestTargets, problemHref } from "@/lib/contest-context";

describe("contest context helpers", () => {
  it("preserves ?contest= when linking from a contest submission", () => {
    expect(problemHref("a-plus-b", 7)).toBe("/problems/a-plus-b?contest=7");
    expect(problemHref("a-plus-b", null)).toBe("/problems/a-plus-b");
    expect(problemHref("a-plus-b", undefined)).toBe("/problems/a-plus-b");
  });

  it("returns active contest banner targets only when ?contest= is missing", () => {
    const active = [{ id: 7, title: "Midterm Cup", letter: "B" }];
    expect(missingContestTargets(null, active)).toEqual(active);
    expect(missingContestTargets("7", active)).toEqual([]);
    expect(missingContestTargets(null, [])).toEqual([]);
    expect(missingContestTargets(null, undefined)).toEqual([]);
  });
});
