import { NextRequest, NextResponse } from "next/server";

import {
  backendBase,
  clearAuthCookies,
  getRefreshToken,
} from "@/lib/auth-cookies";
import { rejectCrossOrigin } from "@/lib/same-origin";

export async function POST(req: NextRequest) {
  const refused = rejectCrossOrigin(req);
  if (refused) return refused;
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
