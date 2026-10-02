"use client";

import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";

import { formatApiErrorPayload } from "@/lib/admin";
import { ApiError, apiFetch } from "@/lib/api";
import type { AdminUser } from "@/lib/types";

type Props = {
  user: AdminUser;
  onResetPassword: (user: AdminUser) => void;
  onDelete: (user: AdminUser) => void;
  /** The signed-in admin's own row: the server refuses disabling or
   *  deleting yourself, so those actions are not offered. */
  isSelf?: boolean;
};

type EditableFields = Pick<
  AdminUser,
  "first_name" | "last_name" | "school_id" | "class_section" | "role"
>;

function errorText(err: Error) {
  return err instanceof ApiError ? formatApiErrorPayload(err.payload, err.message) : err.message;
}

const inputClass = "w-full rounded border border-slate-700 bg-slate-900 px-2 py-1 text-xs";

/** One roster row: view, inline edit, enable/disable, reset, delete. */
export function AccountRow({ user, onResetPassword, onDelete, isSelf = false }: Props) {
  const queryClient = useQueryClient();
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState<EditableFields>(user);
  const [error, setError] = useState<string | null>(null);

  const patch = useMutation({
    mutationFn: (body: Partial<AdminUser>) =>
      apiFetch<AdminUser>(`/users/${user.id}/`, { method: "PATCH", body: JSON.stringify(body) }),
    onSuccess: () => {
      setEditing(false);
      setError(null);
      void queryClient.invalidateQueries({ queryKey: ["admin", "users"] });
    },
    onError: (err: Error) => setError(errorText(err)),
  });

  function startEdit() {
    setDraft({
      first_name: user.first_name,
      last_name: user.last_name,
      school_id: user.school_id,
      class_section: user.class_section,
      role: user.role,
    });
    setError(null);
    setEditing(true);
  }

  const field = (name: keyof Omit<EditableFields, "role">, label: string) => (
    <input
      aria-label={label}
      placeholder={label}
      className={inputClass}
      value={draft[name]}
      onChange={(e) => setDraft((d) => ({ ...d, [name]: e.target.value }))}
    />
  );

  const fullName = [user.first_name, user.last_name].filter(Boolean).join(" ");

  return (
    <tr className="border-t border-slate-800 align-top">
      <td className="px-4 py-3">
        <span className="font-medium text-white">{user.username}</span>
        {editing ? (
          <div className="mt-2 grid gap-1 sm:grid-cols-2">
            {field("first_name", "First name")}
            {field("last_name", "Last name")}
            {field("school_id", "School ID")}
          </div>
        ) : (
          <>
            {fullName && <span className="ml-2 text-slate-300">{fullName}</span>}
            {user.school_id && <span className="ml-2 text-xs text-slate-500">{user.school_id}</span>}
          </>
        )}
        {error && <p className="mt-1 text-xs text-red-300">{error}</p>}
      </td>
      <td className="px-4 py-3 capitalize text-slate-300">
        {editing ? (
          <select
            aria-label="Role"
            className={inputClass}
            value={draft.role}
            onChange={(e) => setDraft((d) => ({ ...d, role: e.target.value as AdminUser["role"] }))}
          >
            <option value="student">Student</option>
            <option value="admin">Admin</option>
          </select>
        ) : (
          user.role
        )}
      </td>
      <td className="px-4 py-3 text-slate-400">
        {editing ? field("class_section", "Section") : user.class_section || "—"}
      </td>
      <td className="px-4 py-3">
        <span className={user.is_active ? "text-slate-400" : "text-amber-300"}>
          {user.is_active ? "Active" : "Disabled"}
        </span>
      </td>
      <td className="space-x-3 whitespace-nowrap px-4 py-3 text-xs">
        {editing ? (
          <>
            <button
              type="button"
              onClick={() => patch.mutate(draft)}
              disabled={patch.isPending}
              className="cursor-pointer text-emerald-300 hover:underline disabled:opacity-50"
            >
              Save
            </button>
            <button
              type="button"
              onClick={() => setEditing(false)}
              className="cursor-pointer text-slate-400 hover:text-white"
            >
              Cancel
            </button>
          </>
        ) : (
          <>
            <button type="button" onClick={startEdit} className="cursor-pointer text-emerald-300 hover:underline">
              Edit
            </button>
            {!isSelf && (
              <button
                type="button"
                onClick={() => patch.mutate({ is_active: !user.is_active })}
                disabled={patch.isPending}
                className="cursor-pointer text-amber-300 hover:underline disabled:opacity-50"
              >
                {user.is_active ? "Disable" : "Enable"}
              </button>
            )}
            <button
              type="button"
              onClick={() => onResetPassword(user)}
              className="cursor-pointer text-emerald-300 hover:underline"
            >
              Reset password
            </button>
            {!isSelf && (
              <button
                type="button"
                onClick={() => onDelete(user)}
                className="cursor-pointer text-red-300 hover:text-red-200"
              >
                Delete
              </button>
            )}
          </>
        )}
      </td>
    </tr>
  );
}
