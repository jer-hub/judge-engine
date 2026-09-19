import { NextRequest, NextResponse } from "next/server";

import {
  accessCookieName,
  backendBase,
  cookieOptions,
  refreshCookieName,
} from "@/lib/auth-cookies";

export async function POST(req: NextRequest) {
  const body = await req.json();
  const res = await fetch(`${backendBase()}/api/auth/login/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await res.json();
  if (!res.ok) {
    return NextResponse.json(data, { status: res.status });
  }

  const response = NextResponse.json({ ok: true });
  response.cookies.set(accessCookieName(), data.access, cookieOptions(60 * 60));
  response.cookies.set(
    refreshCookieName(),
    data.refresh,
    cookieOptions(60 * 60 * 24 * 7),
  );
  return response;
}
