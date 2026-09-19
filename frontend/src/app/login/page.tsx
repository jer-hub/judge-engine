"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });
      const data = await res.json();
      if (!res.ok) {
        setError(data.detail || "Login failed");
        return;
      }
      router.push("/problems");
      router.refresh();
    } catch {
      setError("Could not reach the server");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto max-w-md">
      <h1 className="mb-2 text-3xl font-semibold text-white">Sign in</h1>
      <p className="mb-6 text-sm text-slate-400">
        Accounts are created by your teacher in Django Admin. There is no public registration.
      </p>
      <form onSubmit={onSubmit} className="space-y-4 rounded-xl border border-slate-800 bg-slate-900/50 p-6">
        <label className="block text-sm">
          <span className="text-slate-300">Username</span>
          <input
            className="mt-1 w-full rounded border border-slate-700 bg-slate-950 px-3 py-2"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoComplete="username"
            required
          />
        </label>
        <label className="block text-sm">
          <span className="text-slate-300">Password</span>
          <input
            type="password"
            className="mt-1 w-full rounded border border-slate-700 bg-slate-950 px-3 py-2"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
            required
          />
        </label>
        {error && <p className="text-sm text-red-300">{error}</p>}
        <button
          type="submit"
          disabled={loading}
          className="w-full rounded bg-emerald-600 px-4 py-2 font-medium text-white hover:bg-emerald-500 disabled:opacity-60"
        >
          {loading ? "Signing in…" : "Sign in"}
        </button>
      </form>
    </div>
  );
}
