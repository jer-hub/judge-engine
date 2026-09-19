export default function AdminLoading() {
  return (
    <div className="space-y-6" aria-busy="true" aria-label="Loading admin">
      <div className="h-16 max-w-md animate-pulse rounded-lg bg-slate-900" />
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="h-28 animate-pulse rounded-xl bg-slate-900" />
        ))}
      </div>
      <div className="h-64 animate-pulse rounded-xl bg-slate-900" />
    </div>
  );
}
