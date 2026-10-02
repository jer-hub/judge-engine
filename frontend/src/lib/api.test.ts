import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError, apiFetch } from "@/lib/api";

function jsonResponse(status: number, body: unknown) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

describe("apiFetch", () => {
  const fetchMock = vi.fn();
  const assign = vi.fn();

  beforeEach(() => {
    vi.stubGlobal("fetch", fetchMock);
    vi.stubGlobal("window", { location: { pathname: "/problems/x", search: "?contest=3", assign } });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    fetchMock.mockReset();
    assign.mockReset();
  });

  it("drops the trailing slash before the query (no 308 round trip)", async () => {
    fetchMock.mockImplementation(async () => jsonResponse(200, { ok: true }));
    await apiFetch("/problems/?page_size=100&search=a/b");
    expect(fetchMock.mock.calls[0][0]).toBe("/api/proxy/problems?page_size=100&search=a/b");
    await apiFetch("/auth/me/");
    expect(fetchMock.mock.calls[1][0]).toBe("/api/proxy/auth/me");
  });

  it("throws ApiError with the backend's detail", async () => {
    fetchMock.mockResolvedValue(jsonResponse(400, { detail: "Nope." }));
    const err = await apiFetch<never>("/x/").catch((e: ApiError) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(err.status).toBe(400);
    expect(err.message).toBe("Nope.");
    expect(assign).not.toHaveBeenCalled();
  });

  it("sends an expired session to login and back, query included", async () => {
    fetchMock.mockResolvedValue(jsonResponse(401, { detail: "expired" }));
    await expect(apiFetch("/submissions/")).rejects.toBeInstanceOf(ApiError);
    expect(assign).toHaveBeenCalledWith("/login?next=%2Fproblems%2Fx%3Fcontest%3D3");
  });

  it("does not redirect from the login page itself", async () => {
    vi.stubGlobal("window", { location: { pathname: "/login", search: "", assign } });
    fetchMock.mockResolvedValue(jsonResponse(401, {}));
    await expect(apiFetch("/auth/me/")).rejects.toBeInstanceOf(ApiError);
    expect(assign).not.toHaveBeenCalled();
  });
});
