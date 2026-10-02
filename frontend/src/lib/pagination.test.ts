import { afterEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/api", () => ({ apiFetch: vi.fn() }));

import { apiFetch } from "@/lib/api";
import { buildListQuery, fetchAllPages, pageRange } from "@/lib/pagination";

describe("buildListQuery", () => {
  it("adds a trailing slash and skips empty params", () => {
    expect(buildListQuery("/users", { search: "", page: 2, role: undefined, page_size: 50 })).toBe(
      "/users/?page=2&page_size=50",
    );
    expect(buildListQuery("/users/")).toBe("/users/");
  });
});

describe("fetchAllPages", () => {
  afterEach(() => vi.mocked(apiFetch).mockReset());

  it("follows pages until there is no next one", async () => {
    vi.mocked(apiFetch)
      .mockResolvedValueOnce({ count: 3, next: "http://backend:8000/api/users/?page=2", previous: null, results: [1, 2] })
      .mockResolvedValueOnce({ count: 3, next: null, previous: "x", results: [3] });
    const all = await fetchAllPages<number>("/users/");
    expect(all.results).toEqual([1, 2, 3]);
    // Pages are requested by number: `next` is an internal backend URL.
    expect(vi.mocked(apiFetch).mock.calls.map((c) => c[0])).toEqual([
      "/users/?page_size=100&page=1",
      "/users/?page_size=100&page=2",
    ]);
  });
});

describe("pageRange", () => {
  it("clamps the page and reports the visible span", () => {
    expect(pageRange(45, 3, 20)).toEqual({ from: 41, to: 45, totalPages: 3 });
    expect(pageRange(45, 9, 20)).toEqual({ from: 41, to: 45, totalPages: 3 });
    expect(pageRange(0, 1, 20)).toEqual({ from: 0, to: 0, totalPages: 0 });
  });
});
