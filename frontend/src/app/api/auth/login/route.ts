import { NextRequest, NextResponse } from "next/server";

import {
  backendBase,
  clientIp,
  forwardedHeaders,
  setAuthCookies,
} from "@/lib/auth-cookies";
import { rejectCrossOrigin } from "@/lib/same-origin";

export async function POST(req: NextRequest) {
  // Login CSRF: don't let another site sign a student into an attacker's account.
  const refused = rejectCrossOrigin(req);
  if (refused) return refused;
  const body = await req.json().catch(() => null);
  if (!body || typeof body !== "object") {
    return NextResponse.json({ detail: "Invalid request." }, { status: 400 });
  }
  const res = await fetch(`${backendBase()}/api/auth/login/`, {
    method: "POST",
    // Forward the client IP so Django throttles per student, not per frontend.
    headers: forwardedHeaders(clientIp(req), {
      "Content-Type": "application/json",
    }),
    body: JSON.stringify(body),
  });
  const data = await res.json().catch(() => null);
  if (!res.ok || !data) {
    return NextResponse.json(
      data ?? { detail: "Login service unavailable. Please retry." },
      { status: res.ok ? 502 : res.status },
    );
  }

  const response = NextResponse.json({ ok: true });
  setAuthCookies(response, { access: data.access, refresh: data.refresh });
  return response;
}
