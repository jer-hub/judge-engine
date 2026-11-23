"use client";

import { useEffect, useId, useRef } from "react";

type Props = {
  open: boolean;
  title: string;
  body: string;
  confirmLabel?: string;
  cancelLabel?: string;
  danger?: boolean;
  /** The confirmed action is running: disable Confirm so it cannot fire twice. */
  busy?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
};

function focusableIn(root: HTMLElement): HTMLElement[] {
  return Array.from(
    root.querySelectorAll<HTMLElement>(
      'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
    ),
  ).filter((el) => !el.hasAttribute("disabled") && el.tabIndex !== -1);
}

export function ConfirmDialog({
  open,
  title,
  body,
  confirmLabel = "Confirm",
  cancelLabel = "Cancel",
  danger = false,
  busy = false,
  onConfirm,
  onCancel,
}: Props) {
  const titleId = useId();
  const bodyId = useId();
  const panelRef = useRef<HTMLDivElement>(null);
  const confirmRef = useRef<HTMLButtonElement>(null);
  const cancelRef = useRef<HTMLButtonElement>(null);
  // Callers pass inline arrows; read the latest through a ref so a parent
  // re-render does not re-run the effect and steal focus back.
  const onCancelRef = useRef(onCancel);
  onCancelRef.current = onCancel;

  useEffect(() => {
    if (!open) return;
    const previous = document.activeElement as HTMLElement | null;
    // A destructive action should not be one stray Enter away.
    (danger ? cancelRef : confirmRef).current?.focus();
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") {
        onCancelRef.current();
        return;
      }
      if (e.key !== "Tab" || !panelRef.current) return;
      const nodes = focusableIn(panelRef.current);
      if (nodes.length === 0) return;
      const first = nodes[0];
      const last = nodes[nodes.length - 1];
      const active = document.activeElement as HTMLElement | null;
      if (e.shiftKey && active === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && active === last) {
        e.preventDefault();
        first.focus();
      }
    }
    window.addEventListener("keydown", onKey);
    return () => {
      window.removeEventListener("keydown", onKey);
      previous?.focus?.();
    };
  }, [open, danger]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/70 p-4 backdrop-blur-xs"
      role="presentation"
      onClick={onCancel}
    >
      <div
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={bodyId}
        className="w-full max-w-md rounded-xl border border-slate-700 bg-slate-900 p-5 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 id={titleId} className="text-lg font-semibold text-white">
          {title}
        </h2>
        <p id={bodyId} className="mt-2 text-sm text-slate-400">
          {body}
        </p>
        <div className="mt-5 flex justify-end gap-2">
          <button
            ref={cancelRef}
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
            disabled={busy}
            aria-busy={busy}
            className={`cursor-pointer rounded-lg px-3 py-2 text-sm font-medium transition disabled:cursor-not-allowed disabled:opacity-60 ${
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
