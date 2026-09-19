"use client";

import { FormEvent, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { EmptyState } from "@/components/EmptyState";
import { formatApiErrorPayload } from "@/lib/admin";
import { ApiError, apiFetch } from "@/lib/api";
import type { AdminUser, Paginated } from "@/lib/types";

import { AccountsImport } from "./AccountsImport";
import { UsersIcon } from "./icons";

export function AccountsPanel() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [formOpen, setFormOpen] = useState(false);
  const [importOpen, setImportOpen] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [resetFor, setResetFor] = useState<AdminUser | null>(null);
  const [newPassword, setNewPassword] = useState("");
  const [form, setForm] = useState({
    username: "",
    password: "",
    role: "student" as "student" | "admin",
    school_id: "",
    class_section: "",
    email: "",
  });

  const { data, isLoading, error } = useQuery({
    queryKey: ["admin", "users", search],
    queryFn: () => {
      const qs = search.trim()
        ? `/users/?search=${encodeURIComponent(search.trim())}`
        : "/users/?page_size=50";
      return apiFetch<Paginated<AdminUser>>(qs);
    },
  });

  const createMutation = useMutation({
    mutationFn: () =>
      apiFetch<AdminUser>("/users/", {
        method: "POST",
        body: JSON.stringify(form),
      }),
    onSuccess: () => {
      setFormOpen(false);
      setFormError(null);
      setForm({
        username: "",
        password: "",
        role: "student",
        school_id: "",
        class_section: "",
        email: "",
      });
      void queryClient.invalidateQueries({ queryKey: ["admin", "users"] });
    },
    onError: (err: Error) => {
      setFormError(
        err instanceof ApiError
          ? formatApiErrorPayload(err.payload, err.message)
          : err.message,
      );
    },
  });

  const resetMutation = useMutation({
    mutationFn: () =>
      apiFetch<{ detail: string }>(`/users/${resetFor!.id}/reset-password/`, {
        method: "POST",
        body: JSON.stringify({ password: newPassword }),
      }),
    onSuccess: () => {
      setResetFor(null);
      setNewPassword("");
      setFormError(null);
    },
    onError: (err: Error) => {
      setFormError(
        err instanceof ApiError
          ? formatApiErrorPayload(err.payload, err.message)
          : err.message,
      );
    },
  });

  function onCreate(e: FormEvent) {
    e.preventDefault();
    setFormError(null);
    if (form.password.length < 8) {
      setFormError("Password must be at least 8 characters.");
      return;
    }
    createMutation.mutate();
  }

  return (
    <div className="space-y-4">
      <div className="rounded-xl border border-slate-800 bg-slate-950/50 p-5">
        <div className="mb-3 flex items-center gap-2 text-emerald-300">
          <UsersIcon className="h-5 w-5" aria-hidden="true" />
          <h3 className="font-medium text-white">Roster</h3>
        </div>
        <p className="max-w-2xl text-sm leading-relaxed text-slate-400">
          Admin-created accounts only — no public registration. Create students or teachers
          one at a time, or import a CSV roster. Reset passwords when needed.
        </p>
        <div className="mt-4 flex flex-wrap gap-2">
          <input
            className="rounded border border-slate-700 bg-slate-900 px-3 py-2 text-sm"
            placeholder="Search username / class / school id"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <button
            type="button"
            onClick={() => setFormOpen((v) => !v)}
            className="cursor-pointer rounded-lg bg-emerald-500 px-3 py-2 text-sm font-medium text-slate-950 hover:bg-emerald-400"
          >
            {formOpen ? "Close form" : "New account"}
          </button>
          <button
            type="button"
            onClick={() => setImportOpen((v) => !v)}
            className="cursor-pointer rounded-lg border border-slate-600 px-3 py-2 text-sm text-slate-200 hover:border-slate-400"
          >
            {importOpen ? "Close import" : "Import CSV"}
          </button>
        </div>
      </div>

      {importOpen && (
        <AccountsImport
          onImported={() => {
            void queryClient.invalidateQueries({ queryKey: ["admin", "users"] });
          }}
        />
      )}

      {formOpen && (
        <form
          onSubmit={onCreate}
          className="grid gap-3 rounded-xl border border-slate-800 bg-slate-950/50 p-4 sm:grid-cols-2"
        >
          <label className="block text-sm">
            <span className="mb-1 block text-slate-400">Username</span>
            <input
              className="w-full rounded border border-slate-700 bg-slate-900 px-3 py-2"
              value={form.username}
              onChange={(e) => setForm((p) => ({ ...p, username: e.target.value }))}
              required
            />
          </label>
          <label className="block text-sm">
            <span className="mb-1 block text-slate-400">Password</span>
            <input
              type="password"
              className="w-full rounded border border-slate-700 bg-slate-900 px-3 py-2"
              value={form.password}
              onChange={(e) => setForm((p) => ({ ...p, password: e.target.value }))}
              required
              minLength={8}
            />
          </label>
          <label className="block text-sm">
            <span className="mb-1 block text-slate-400">Role</span>
            <select
              className="w-full rounded border border-slate-700 bg-slate-900 px-3 py-2"
              value={form.role}
              onChange={(e) =>
                setForm((p) => ({
                  ...p,
                  role: e.target.value as "student" | "admin",
                }))
              }
            >
              <option value="student">Student</option>
              <option value="admin">Admin / teacher</option>
            </select>
          </label>
          <label className="block text-sm">
            <span className="mb-1 block text-slate-400">Email</span>
            <input
              type="email"
              className="w-full rounded border border-slate-700 bg-slate-900 px-3 py-2"
              value={form.email}
              onChange={(e) => setForm((p) => ({ ...p, email: e.target.value }))}
            />
          </label>
          <label className="block text-sm">
            <span className="mb-1 block text-slate-400">School ID</span>
            <input
              className="w-full rounded border border-slate-700 bg-slate-900 px-3 py-2"
              value={form.school_id}
              onChange={(e) => setForm((p) => ({ ...p, school_id: e.target.value }))}
            />
          </label>
          <label className="block text-sm">
            <span className="mb-1 block text-slate-400">Class section</span>
            <input
              className="w-full rounded border border-slate-700 bg-slate-900 px-3 py-2"
              value={form.class_section}
              onChange={(e) =>
                setForm((p) => ({ ...p, class_section: e.target.value }))
              }
            />
          </label>
          {formError && <p className="text-sm text-red-300 sm:col-span-2">{formError}</p>}
          <div className="sm:col-span-2">
            <button
              type="submit"
              disabled={createMutation.isPending}
              className="cursor-pointer rounded-lg bg-emerald-500 px-4 py-2 text-sm font-medium text-slate-950 hover:bg-emerald-400 disabled:opacity-60"
            >
              {createMutation.isPending ? "Creating…" : "Create account"}
            </button>
          </div>
        </form>
      )}

      {resetFor && (
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (newPassword.length < 8) {
              setFormError("Password must be at least 8 characters.");
              return;
            }
            resetMutation.mutate();
          }}
          className="flex flex-wrap items-end gap-2 rounded-xl border border-amber-900/40 bg-amber-950/20 p-4"
        >
          <label className="block min-w-[220px] flex-1 text-sm">
            <span className="mb-1 block text-slate-300">
              New password for {resetFor.username}
            </span>
            <input
              type="password"
              className="w-full rounded border border-slate-700 bg-slate-900 px-3 py-2"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              minLength={8}
              required
            />
          </label>
          <button
            type="submit"
            className="cursor-pointer rounded bg-amber-500 px-3 py-2 text-sm font-medium text-slate-950 hover:bg-amber-400"
          >
            Reset
          </button>
          <button
            type="button"
            onClick={() => {
              setResetFor(null);
              setNewPassword("");
            }}
            className="cursor-pointer rounded border border-slate-700 px-3 py-2 text-sm text-slate-300"
          >
            Cancel
          </button>
        </form>
      )}

      {formError && !formOpen && <p className="text-sm text-red-300">{formError}</p>}
      {isLoading && <p className="text-sm text-slate-400">Loading users…</p>}
      {error && <p className="text-sm text-red-300">{(error as Error).message}</p>}

      {!isLoading && (data?.results?.length ?? 0) === 0 && (
        <EmptyState title="No users found" body="Create a student account to get started." />
      )}

      {(data?.results?.length ?? 0) > 0 && (
        <div className="overflow-x-auto rounded-xl border border-slate-800">
          <table className="w-full min-w-[640px] text-left text-sm">
            <thead className="bg-slate-900/80 text-slate-400">
              <tr>
                <th className="px-4 py-3">User</th>
                <th className="px-4 py-3">Role</th>
                <th className="px-4 py-3">Class</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3">Actions</th>
              </tr>
            </thead>
            <tbody>
              {data?.results.map((u) => (
                <tr key={u.id} className="border-t border-slate-800">
                  <td className="px-4 py-3">
                    <span className="font-medium text-white">{u.username}</span>
                    {u.school_id && (
                      <span className="ml-2 text-xs text-slate-500">{u.school_id}</span>
                    )}
                  </td>
                  <td className="px-4 py-3 capitalize text-slate-300">{u.role}</td>
                  <td className="px-4 py-3 text-slate-400">{u.class_section || "—"}</td>
                  <td className="px-4 py-3 text-slate-400">
                    {u.is_active ? "Active" : "Disabled"}
                  </td>
                  <td className="px-4 py-3">
                    <button
                      type="button"
                      onClick={() => {
                        setResetFor(u);
                        setNewPassword("");
                      }}
                      className="cursor-pointer text-xs text-emerald-300 hover:underline"
                    >
                      Reset password
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
