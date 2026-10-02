import { NextRequest } from "next/server";
import { describe, expect, it } from "vitest";

import { middleware } from "@/middleware";

function visit(path: string, cookie?: string) {
  return middleware(
    new NextRequest(`http://localhost:3000${path}`, {
      headers: cookie ? { cookie } : {},
    }),
  );
}

describe("middleware", () => {
  it("sends a visitor without a session to login, keeping the query", () => {
    const res = visit("/problems/a-plus-b?contest=3");
    expect(res.status).toBe(307);
    const location = new URL(res.headers.get("location")!);
    expect(location.pathname).toBe("/login");
    expect(location.searchParams.get("next")).toBe("/problems/a-plus-b?contest=3");
  });

  it("lets a session through, even when only the refresh cookie is left", () => {
    expect(visit("/problems", "je_access=a").headers.get("location")).toBeNull();
    expect(visit("/problems", "je_refresh=r").headers.get("location")).toBeNull();
  });

  it("never gates the login page or the API routes", () => {
    expect(visit("/login").headers.get("location")).toBeNull();
    expect(visit("/api/proxy/auth/me").headers.get("location")).toBeNull();
  });
});
