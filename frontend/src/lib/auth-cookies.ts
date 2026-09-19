import { cookies } from "next/headers";

const ACCESS = "je_access";
const REFRESH = "je_refresh";

export function accessCookieName() {
  return ACCESS;
}

export function refreshCookieName() {
  return REFRESH;
}

export function cookieOptions(maxAge: number) {
  // Secure by default in production; allow explicit override for local HTTP.
  const secure =
    process.env.JWT_COOKIE_SECURE === "true" ||
    (process.env.JWT_COOKIE_SECURE !== "false" &&
      process.env.NODE_ENV === "production");
  return {
    httpOnly: true,
    secure,
    sameSite: "lax" as const,
    path: "/",
    maxAge,
  };
}

export async function getAccessToken() {
  const jar = await cookies();
  return jar.get(ACCESS)?.value || null;
}

export function backendBase() {
  return (
    process.env.INTERNAL_API_URL ||
    process.env.NEXT_PUBLIC_API_URL ||
    "http://localhost:8000"
  );
}
