"use client";

export default function AdminError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="rounded-xl border border-red-900/60 bg-red-950/30 p-6">
      <h2 className="text-lg font-semibold text-red-200">Admin console failed to load</h2>
      <p className="mt-2 text-sm text-red-200/80">{error.message}</p>
      <button
        type="button"
        onClick={reset}
        className="mt-4 cursor-pointer rounded-lg border border-red-800 px-3 py-2 text-sm text-red-100 transition hover:bg-red-900/40"
      >
        Try again
      </button>
    </div>
  );
}
