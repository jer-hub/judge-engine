import { cookies } from "next/headers";
import { NextResponse } from "next/server";

import {
  accessCookieName,
  backendBase,
  refreshCookieName,
} from "@/lib/auth-cookies";

export async function POST() {
  const jar = await cookies();
  const refresh = jar.get(refreshCookieName())?.value;

  if (refresh) {
    try {
      await fetch(`${backendBase()}/api/auth/logout/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh }),
      });
    } catch {
      // Cookie clear still proceeds
    }
  }

  const response = NextResponse.json({ ok: true });
  response.cookies.set(accessCookieName(), "", {
    httpOnly: true,
    path: "/",
    maxAge: 0,
  });
  response.cookies.set(refreshCookieName(), "", {
    httpOnly: true,
    path: "/",
    maxAge: 0,
  });
  return response;
}
