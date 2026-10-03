import { describe, expect, it } from "vitest";

import { backendApiUrl } from "@/lib/proxy-path";

const BASE = "http://backend:8000";

describe("backendApiUrl", () => {
  it("builds API URLs with a trailing slash and the query", () => {
    expect(backendApiUrl(BASE, ["problems", "a-plus-b"], "?page=2")).toBe(
      "http://backend:8000/api/problems/a-plus-b/?page=2",
    );
    expect(backendApiUrl(`${BASE}/`, ["auth", "me"])).toBe("http://backend:8000/api/auth/me/");
  });

  it.each([
    [[".."]],
    [["..", "admin", "login"]],
    [["..%2Fadmin"]],
    [["../admin"]],
    [["..\\admin"]],
    [["."]],
    [["problems", ""]],
    [["a?b"]],
    [["a#b"]],
    [["a\nb"]],
  ])("refuses path %j", (parts) => {
    expect(backendApiUrl(BASE, parts)).toBeNull();
  });
});
