import { afterEach, describe, expect, it, vi } from "vitest";

import { cookieOptions, refreshTokens } from "@/lib/auth-cookies";

function jsonResponse(status: number, body: unknown) {
  return new Response(JSON.stringify(body), { status });
}

describe("refreshTokens", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("shares one refresh between parallel requests (rotation would fail the rest)", async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(200, { access: "A2", refresh: "R2" }));
    vi.stubGlobal("fetch", fetchMock);
    const [a, b] = await Promise.all([refreshTokens("shared-R1", null), refreshTokens("shared-R1", null)]);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(a).toEqual({ ok: true, tokens: { access: "A2", refresh: "R2" } });
    expect(b).toBe(a);
  });

  it("keeps the old refresh token when the backend doesn't rotate", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse(200, { access: "A2" })));
    expect(await refreshTokens("norotate-R1", null)).toEqual({
      ok: true,
      tokens: { access: "A2", refresh: "norotate-R1" },
    });
  });

  it("tells a dead session (401) apart from a transient failure", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse(401, {})));
    expect(await refreshTokens("dead-R1", null)).toEqual({ ok: false, reason: "invalid" });
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse(502, {})));
    expect(await refreshTokens("flaky-R1", null)).toEqual({ ok: false, reason: "error" });
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("network down")));
    expect(await refreshTokens("offline-R1", null)).toEqual({ ok: false, reason: "error" });
  });
});

describe("cookieOptions", () => {
  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it("is httpOnly and SameSite=Lax", () => {
    expect(cookieOptions(60)).toMatchObject({ httpOnly: true, sameSite: "lax", path: "/", maxAge: 60 });
  });

  it("is Secure in production unless explicitly turned off", () => {
    vi.stubEnv("NODE_ENV", "production");
    vi.stubEnv("JWT_COOKIE_SECURE", "");
    expect(cookieOptions(60).secure).toBe(true);
    vi.stubEnv("JWT_COOKIE_SECURE", "false");
    expect(cookieOptions(60).secure).toBe(false);
    vi.stubEnv("NODE_ENV", "development");
    vi.stubEnv("JWT_COOKIE_SECURE", "true");
    expect(cookieOptions(60).secure).toBe(true);
  });
});
