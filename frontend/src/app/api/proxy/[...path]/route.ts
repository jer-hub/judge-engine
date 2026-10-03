import { NextRequest, NextResponse } from "next/server";

import {
  backendBase,
  clearAuthCookies,
  clientIp,
  forwardedHeaders,
  getAccessToken,
  getRefreshToken,
  refreshTokens,
  setAuthCookies,
  type RefreshResult,
} from "@/lib/auth-cookies";
import { backendApiUrl } from "@/lib/proxy-path";
import { rejectCrossOrigin } from "@/lib/same-origin";

// Next 15: dynamic route params arrive as a Promise.
type RouteContext = { params: Promise<{ path: string[] }> };

export async function GET(
  req: NextRequest,
  context: RouteContext,
) {
  return proxy(req, (await context.params).path);
}

export async function POST(
  req: NextRequest,
  context: RouteContext,
) {
  return proxy(req, (await context.params).path);
}

export async function PUT(
  req: NextRequest,
  context: RouteContext,
) {
  return proxy(req, (await context.params).path);
}

export async function PATCH(
  req: NextRequest,
  context: RouteContext,
) {
  return proxy(req, (await context.params).path);
}

export async function DELETE(
  req: NextRequest,
  context: RouteContext,
) {
  return proxy(req, (await context.params).path);
}

async function proxy(req: NextRequest, pathParts: string[]) {
  const refused = rejectCrossOrigin(req);
  if (refused) return refused;

  const url = backendApiUrl(backendBase(), pathParts, req.nextUrl.search || "");
  if (url === null) {
    return NextResponse.json({ detail: "Invalid path." }, { status: 400 });
  }

  const ip = clientIp(req);
  let access = await getAccessToken();
  const refresh = await getRefreshToken();
  let result: RefreshResult | null = null;

  // Access cookie expired (its maxAge matches the token's) but the session is
  // still alive: renew before calling, rather than spending a 401 round trip.
  if (!access && refresh) {
    result = await refreshTokens(refresh, ip);
    if (result.ok) access = result.tokens.access;
  }

  const headers = forwardedHeaders(ip);
  const contentType = req.headers.get("content-type");
  if (contentType) headers.set("Content-Type", contentType);
  if (access) headers.set("Authorization", `Bearer ${access}`);

  const init: RequestInit = {
    method: req.method,
    headers,
    body: ["GET", "HEAD"].includes(req.method) ? undefined : await req.text(),
    cache: "no-store",
  };

  let upstream = await fetch(url, init);
  if (upstream.status === 401 && refresh && result === null) {
    result = await refreshTokens(refresh, ip);
    if (result.ok) {
      headers.set("Authorization", `Bearer ${result.tokens.access}`);
      upstream = await fetch(url, { ...init, headers });
    }
  }

  const responseHeaders = new Headers({
    "Content-Type": upstream.headers.get("Content-Type") || "application/json",
  });
  // File downloads (standings CSV) name themselves through this header.
  const disposition = upstream.headers.get("Content-Disposition");
  if (disposition) responseHeaders.set("Content-Disposition", disposition);
  const response = new NextResponse(upstream.body, {
    status: upstream.status,
    headers: responseHeaders,
  });
  if (result?.ok) {
    setAuthCookies(response, result.tokens);
  } else if (result?.reason === "invalid") {
    // Dead session: drop the cookies so the middleware sends the user to /login.
    clearAuthCookies(response);
  }
  return response;
}
