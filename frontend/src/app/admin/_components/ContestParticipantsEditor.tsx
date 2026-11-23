"use client";

import { useState } from "react";

import type { AdminUser } from "@/lib/types";

type Props = {
  participantSet: string[];
  unknownParticipants: string[];
  rosterUsers: AdminUser[];
  rosterLoading: boolean;
  onToggleParticipant: (username: string) => void;
  onApplyPaste: (raw: string) => void;
};

export function ContestParticipantsEditor({
  participantSet,
  unknownParticipants,
  rosterUsers,
  rosterLoading,
  onToggleParticipant,
  onApplyPaste,
}: Props) {
  const [rosterSearch, setRosterSearch] = useState("");
  const [pasteBuffer, setPasteBuffer] = useState("");
  const unknownSet = new Set(unknownParticipants);

  const filteredRoster = rosterUsers.filter((u) => {
    const q = rosterSearch.trim().toLowerCase();
    if (!q) return true;
    return (
      u.username.toLowerCase().includes(q) ||
      u.class_section.toLowerCase().includes(q) ||
      u.school_id.toLowerCase().includes(q)
    );
  });

  function submitPaste() {
    if (!pasteBuffer.trim()) return;
    onApplyPaste(pasteBuffer);
    setPasteBuffer("");
  }

  return (
    <div>
      <h5 className="mb-1 text-sm font-medium text-slate-200">
        Participants{" "}
        <span className="font-normal text-slate-500">
          ({participantSet.length} invited)
        </span>
      </h5>
      <p className="mb-2 text-xs text-slate-500">
        Pre-register students from the roster. They can also self-register if the contest is
        public.
      </p>

      {participantSet.length > 0 && (
        <div className="mb-2 flex flex-wrap gap-1.5">
          {participantSet.map((name) => {
            const unknown = unknownSet.has(name);
            return (
              <button
                key={name}
                type="button"
                onClick={() => onToggleParticipant(name)}
                title="Click to remove"
                aria-label={`Remove participant ${name}`}
                className={`cursor-pointer rounded-full px-2.5 py-0.5 text-xs ${
                  unknown
                    ? "bg-amber-950/60 text-amber-200 ring-1 ring-amber-700"
                    : "bg-slate-800 text-slate-200 hover:bg-slate-700"
                }`}
              >
                {name} ×
              </button>
            );
          })}
        </div>
      )}

      {unknownParticipants.length > 0 && (
        <p className="mb-2 text-xs text-amber-300">
          Highlighted names are not in the roster — remove them before saving.
        </p>
      )}

      <input
        className="mb-2 w-full rounded-sm border border-slate-700 bg-slate-900 px-3 py-1.5 text-sm"
        placeholder="Search roster (username, class, school id)…"
        aria-label="Search roster by username, class, or school id"
        value={rosterSearch}
        onChange={(e) => setRosterSearch(e.target.value)}
      />
      <ul
        aria-label="User roster"
        className="mb-2 max-h-44 space-y-1 overflow-y-auto rounded-sm border border-slate-800 p-2"
      >
        {rosterLoading && (
          <li className="px-2 py-1 text-xs text-slate-500">Loading roster…</li>
        )}
        {!rosterLoading && filteredRoster.length === 0 && (
          <li className="px-2 py-1 text-xs text-slate-500">No users match.</li>
        )}
        {filteredRoster.map((u) => {
          const selected = participantSet.some(
            (n) => n.toLowerCase() === u.username.toLowerCase(),
          );
          return (
            <li key={u.id}>
              <button
                type="button"
                onClick={() => onToggleParticipant(u.username)}
                aria-pressed={selected}
                aria-label={`${selected ? "Remove" : "Add"} ${u.username}`}
                className={`flex w-full cursor-pointer items-center justify-between gap-2 rounded px-2 py-1.5 text-left text-xs hover:bg-slate-800 ${
                  selected ? "bg-emerald-950/40 text-emerald-200" : "text-slate-300"
                }`}
              >
                <span>
                  {u.username}
                  {u.class_section && (
                    <span className="ml-2 text-slate-500">{u.class_section}</span>
                  )}
                </span>
                <span className="text-slate-500">{selected ? "Added" : "Add"}</span>
              </button>
            </li>
          );
        })}
      </ul>

      <div className="flex flex-wrap gap-2">
        <input
          className="min-w-[200px] flex-1 rounded-sm border border-slate-700 bg-slate-900 px-3 py-1.5 font-mono text-xs"
          placeholder="Paste usernames (comma or space separated)"
          aria-label="Paste usernames separated by comma or space"
          value={pasteBuffer}
          onChange={(e) => setPasteBuffer(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              submitPaste();
            }
          }}
        />
        <button
          type="button"
          onClick={submitPaste}
          className="cursor-pointer rounded-sm border border-slate-700 px-3 py-1.5 text-xs text-slate-300 hover:bg-slate-800"
        >
          Add pasted
        </button>
      </div>
    </div>
  );
}
