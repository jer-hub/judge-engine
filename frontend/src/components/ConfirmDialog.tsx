"use client";

import { useEffect, useId, useRef } from "react";

type Props = {
  open: boolean;
  title: string;
  body: string;
  confirmLabel?: string;
  cancelLabel?: string;
  danger?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
};

export function ConfirmDialog({
  open,
  title,
  body,
  confirmLabel = "Confirm",
  cancelLabel = "Cancel",
  danger = false,
  onConfirm,
  onCancel,
}: Props) {
  const titleId = useId();
  const confirmRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!open) return;
    confirmRef.current?.focus();
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onCancel();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onCancel]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/70 p-4 backdrop-blur-sm"
      role="presentation"
      onClick={onCancel}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        className="w-full max-w-md rounded-xl border border-slate-700 bg-slate-900 p-5 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 id={titleId} className="text-lg font-semibold text-white">
          {title}
        </h2>
        <p className="mt-2 text-sm text-slate-400">{body}</p>
        <div className="mt-5 flex justify-end gap-2">
          <button
            type="button"
            onClick={onCancel}
            className="cursor-pointer rounded-lg border border-slate-700 px-3 py-2 text-sm text-slate-300 transition hover:bg-slate-800"
          >
            {cancelLabel}
          </button>
          <button
            ref={confirmRef}
            type="button"
            onClick={onConfirm}
            className={`cursor-pointer rounded-lg px-3 py-2 text-sm font-medium transition ${
              danger
                ? "bg-red-600 text-white hover:bg-red-500"
                : "bg-emerald-500 text-slate-950 hover:bg-emerald-400"
            }`}
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
