import { NextRequest, NextResponse } from "next/server";

import {
  accessCookieName,
  backendBase,
  cookieOptions,
  getAccessToken,
  refreshCookieName,
} from "@/lib/auth-cookies";
import { cookies } from "next/headers";

async function refreshAccess(): Promise<string | null> {
  const jar = await cookies();
  const refresh = jar.get(refreshCookieName())?.value;
  if (!refresh) return null;
  const res = await fetch(`${backendBase()}/api/auth/refresh/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh }),
  });
  if (!res.ok) return null;
  const data = await res.json();
  return data.access as string;
}

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

  let access = await getAccessToken();
  const headers = new Headers();
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
  if (upstream.status === 401) {
    access = await refreshAccess();
    if (access) {
      headers.set("Authorization", `Bearer ${access}`);
      upstream = await fetch(url, { ...init, headers });
      const response = new NextResponse(upstream.body, {
        status: upstream.status,
        headers: {
          "Content-Type":
            upstream.headers.get("Content-Type") || "application/json",
        },
      });
      response.cookies.set(accessCookieName(), access, cookieOptions(60 * 60));
      return response;
    }
  }

  return new NextResponse(upstream.body, {
    status: upstream.status,
    headers: {
      "Content-Type":
        upstream.headers.get("Content-Type") || "application/json",
    },
  });
}
