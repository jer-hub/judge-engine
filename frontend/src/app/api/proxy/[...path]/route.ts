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

export async function GET(
  req: NextRequest,
  context: { params: { path: string[] } },
) {
  return proxy(req, context.params.path);
}

export async function POST(
  req: NextRequest,
  context: { params: { path: string[] } },
) {
  return proxy(req, context.params.path);
}

export async function PUT(
  req: NextRequest,
  context: { params: { path: string[] } },
) {
  return proxy(req, context.params.path);
}

export async function PATCH(
  req: NextRequest,
  context: { params: { path: string[] } },
) {
  return proxy(req, context.params.path);
}

export async function DELETE(
  req: NextRequest,
  context: { params: { path: string[] } },
) {
  return proxy(req, context.params.path);
}

async function proxy(req: NextRequest, pathParts: string[]) {
  // Django APPEND_SLASH cannot redirect POST while keeping the body — always use a trailing slash.
  let path = pathParts.join("/");
  if (path && !path.endsWith("/")) {
    path = `${path}/`;
  }
  const search = req.nextUrl.search || "";
  const url = `${backendBase()}/api/${path}${search}`;

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

  const response = new NextResponse(upstream.body, {
    status: upstream.status,
    headers: {
      "Content-Type":
        upstream.headers.get("Content-Type") || "application/json",
    },
  });
  if (result?.ok) {
    setAuthCookies(response, result.tokens);
  } else if (result?.reason === "invalid") {
    // Dead session: drop the cookies so the middleware sends the user to /login.
    clearAuthCookies(response);
  }
  return response;
}
