import { NextRequest } from "next/server";
import { describe, expect, it } from "vitest";

import { rejectCrossOrigin } from "@/lib/same-origin";

function request(method: string, headers: Record<string, string> = {}, body?: string) {
  return new NextRequest("https://judge.example.edu/api/proxy/submissions", {
    method,
    headers: { host: "judge.example.edu", ...headers },
    body,
  });
}

describe("rejectCrossOrigin", () => {
  it("lets reads through", () => {
    expect(rejectCrossOrigin(request("GET", { "sec-fetch-site": "cross-site" }))).toBeNull();
  });

  it("accepts a same-origin JSON write", () => {
    const req = request("POST", { "sec-fetch-site": "same-origin", "content-type": "application/json" }, "{}");
    expect(rejectCrossOrigin(req)).toBeNull();
  });

  it("refuses a write from another site", () => {
    const res = rejectCrossOrigin(request("POST", { "sec-fetch-site": "same-site" }));
    expect(res?.status).toBe(403);
  });

  it("falls back to Origin when fetch metadata is missing", () => {
    expect(rejectCrossOrigin(request("POST", { origin: "https://evil.example" }))?.status).toBe(403);
    expect(rejectCrossOrigin(request("POST", { origin: "https://judge.example.edu" }))).toBeNull();
  });

  it("refuses form bodies, which an HTML form could forge", () => {
    const req = request(
      "POST",
      { "sec-fetch-site": "same-origin", "content-type": "application/x-www-form-urlencoded" },
      "a=1",
    );
    expect(rejectCrossOrigin(req)?.status).toBe(415);
  });
});
