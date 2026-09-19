"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";

import { djangoAdminUrl } from "@/lib/admin";
import { apiFetch } from "@/lib/api";
import type { User } from "@/lib/types";

const links = [
  { href: "/problems", label: "Problems" },
  { href: "/contests", label: "Contests" },
  { href: "/submissions", label: "Submissions" },
];

export function NavBar() {
  const pathname = usePathname();
  const router = useRouter();
  const { data: user } = useQuery({
    queryKey: ["me"],
    queryFn: () => apiFetch<User>("/auth/me/"),
    retry: false,
  });

  async function logout() {
    await fetch("/api/auth/logout", { method: "POST" });
    router.push("/login");
    router.refresh();
  }

  if (pathname === "/login") return null;

  return (
    <header className="border-b border-slate-800 bg-slate-950/80 backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-3">
        <div className="flex items-center gap-6">
          <Link href="/problems" className="text-lg font-semibold tracking-tight text-emerald-400">
            Judge Engine
          </Link>
          <nav className="flex gap-3 text-sm">
            {links.map((l) => (
              <Link
                key={l.href}
                href={l.href}
                className={
                  pathname.startsWith(l.href)
                    ? "text-white"
                    : "text-slate-400 transition hover:text-white"
                }
              >
                {l.label}
              </Link>
            ))}
            {user?.is_platform_admin && (
              <Link
                href="/admin"
                className={
                  pathname.startsWith("/admin")
                    ? "text-white"
                    : "text-slate-400 transition hover:text-white"
                }
              >
                Admin
              </Link>
            )}
          </nav>
        </div>
        <div className="flex items-center gap-3 text-sm text-slate-300">
          {user ? (
            <>
              <span>
                {user.username}
                <span className="ml-2 rounded bg-slate-800 px-2 py-0.5 text-xs uppercase text-slate-400">
                  {user.role}
                </span>
              </span>
              {user.is_platform_admin && (
                <a
                  href={djangoAdminUrl()}
                  className="text-slate-400 transition hover:text-emerald-400"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  Django
                </a>
              )}
              <button
                type="button"
                onClick={logout}
                className="cursor-pointer rounded border border-slate-700 px-3 py-1 transition hover:bg-slate-800"
              >
                Log out
              </button>
            </>
          ) : (
            <Link href="/login" className="text-emerald-400 hover:underline">
              Log in
            </Link>
          )}
        </div>
      </div>
    </header>
  );
}
