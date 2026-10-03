import { describe, expect, it } from "vitest";

import { safeNextPath } from "@/lib/safe-next";

const ORIGIN = "https://judge.example.edu";

describe("safeNextPath", () => {
  it("keeps local paths with query and hash", () => {
    expect(safeNextPath("/problems/a-plus-b?tab=2#x", ORIGIN)).toBe("/problems/a-plus-b?tab=2#x");
    expect(safeNextPath("/admin", ORIGIN)).toBe("/admin");
  });

  it("falls back when missing or pointing at login", () => {
    expect(safeNextPath(null, ORIGIN)).toBe("/problems");
    expect(safeNextPath("", ORIGIN)).toBe("/problems");
    expect(safeNextPath("/login?next=/x", ORIGIN)).toBe("/problems");
  });

  it.each([
    "//evil.com",
    "/\\evil.com",
    "/\t/evil.com",
    "/\n/evil.com",
    "/\r\n/evil.com",
    "https://evil.com/",
    "javascript:alert(1)",
    "evil.com",
  ])("rejects off-site target %j", (next) => {
    expect(safeNextPath(next, ORIGIN)).toBe("/problems");
  });
});
