import { NextResponse } from "next/server";

import {
  backendBase,
  clearAuthCookies,
  getRefreshToken,
} from "@/lib/auth-cookies";

export async function POST() {
  const refresh = await getRefreshToken();

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
  clearAuthCookies(response);
  return response;
}
