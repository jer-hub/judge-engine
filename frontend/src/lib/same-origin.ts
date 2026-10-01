import { NextRequest, NextResponse } from "next/server";

/**
 * CSRF guard for routes that act with the auth cookies. SameSite=Lax stops
 * cross-site form posts, but not same-site ones (e.g. a sibling subdomain), so
 * unsafe requests must also come from this origin and carry JSON — the one
 * body type a plain HTML form cannot send.
 *
 * Returns a rejection response, or null when the request may proceed.
 */
export function rejectCrossOrigin(req: NextRequest): NextResponse | null {
  if (["GET", "HEAD", "OPTIONS"].includes(req.method)) return null;

  // Fetch metadata, sent by every current browser.
  const site = req.headers.get("sec-fetch-site");
  if (site && site !== "same-origin") return forbidden();

  // Fallback for browsers without it. No Origin at all = not a browser
  // (curl, scripts), which cannot ride a victim's cookies anyway.
  const origin = req.headers.get("origin");
  if (!site && origin) {
    const host = req.headers.get("x-forwarded-host") ?? req.headers.get("host");
    let originHost: string | null = null;
    try {
      originHost = new URL(origin).host;
    } catch {
      return forbidden();
    }
    if (!host || originHost !== host) return forbidden();
  }

  const contentType = req.headers.get("content-type");
  const hasBody = req.headers.get("content-length") !== "0" && contentType !== null;
  if (hasBody && !contentType.toLowerCase().startsWith("application/json")) {
    return NextResponse.json(
      { detail: "Only application/json request bodies are accepted." },
      { status: 415 },
    );
  }
  return null;
}

function forbidden() {
  return NextResponse.json({ detail: "Cross-origin request refused." }, { status: 403 });
}
