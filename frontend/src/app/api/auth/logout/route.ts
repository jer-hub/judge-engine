import { NextRequest, NextResponse } from "next/server";

import {
  backendBase,
  clearAuthCookies,
  clientIp,
  forwardedHeaders,
  getRefreshToken,
} from "@/lib/auth-cookies";
import { rejectCrossOrigin } from "@/lib/same-origin";

export async function POST(req: NextRequest) {
  const refused = rejectCrossOrigin(req);
  if (refused) return refused;
  const refresh = await getRefreshToken();

  if (refresh) {
    try {
      // Forward the client IP like login and refresh do: without it every
      // logout shares the frontend's address and one throttle bucket.
      const res = await fetch(`${backendBase()}/api/auth/logout/`, {
        method: "POST",
        headers: forwardedHeaders(clientIp(req), { "Content-Type": "application/json" }),
        body: JSON.stringify({ refresh }),
      });
      // 400 means the token was already invalid: nothing left to revoke.
      if (!res.ok && res.status !== 400) {
        console.error(`Logout: refresh token not revoked (backend ${res.status})`);
      }
    } catch (err) {
      console.error("Logout: refresh token not revoked (backend unreachable)", err);
    }
  }

  // Clear the cookies regardless, so this browser is signed out.
  const response = NextResponse.json({ ok: true });
  clearAuthCookies(response);
  return response;
}
