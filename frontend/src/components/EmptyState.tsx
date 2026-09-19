type Props = {
  title: string;
  body?: string;
  actionLabel?: string;
  onAction?: () => void;
};

export function EmptyState({ title, body, actionLabel, onAction }: Props) {
  return (
    <div className="rounded-xl border border-dashed border-slate-700 bg-slate-950/40 px-6 py-12 text-center">
      <h3 className="text-base font-medium text-white">{title}</h3>
      {body && <p className="mt-2 text-sm text-slate-400">{body}</p>}
      {actionLabel && onAction && (
        <button
          type="button"
          onClick={onAction}
          className="mt-4 cursor-pointer rounded-lg border border-slate-700 px-3 py-2 text-sm text-slate-200 transition hover:bg-slate-800"
        >
          {actionLabel}
        </button>
      )}
    </div>
  );
}
