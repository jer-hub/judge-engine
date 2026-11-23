"use client";

type Props = {
  exportSection: string;
  onExportSectionChange: (v: string) => void;
  participantSections: string[];
  exporting: boolean;
  onExportStandings: () => void;
  exportingSolutions: boolean;
  onExportSolutions: () => void;
  rejudgePending: boolean;
  onRequestRejudge: () => void;
};

export function ContestExportsBar({
  exportSection,
  onExportSectionChange,
  participantSections,
  exporting,
  onExportStandings,
  exportingSolutions,
  onExportSolutions,
  rejudgePending,
  onRequestRejudge,
}: Props) {
  return (
    <div className="flex flex-wrap items-center gap-2 rounded-sm border border-slate-800 bg-slate-900/40 p-3 text-xs">
      <span className="text-slate-400">Results</span>
      <select
        aria-label="Section to export"
        className="rounded-sm border border-slate-700 bg-slate-900 px-2 py-1"
        value={exportSection}
        onChange={(e) => onExportSectionChange(e.target.value)}
      >
        <option value="">All sections</option>
        {participantSections.map((s) => (
          <option key={s} value={s}>
            {s}
          </option>
        ))}
      </select>
      <button
        type="button"
        onClick={onExportStandings}
        disabled={exporting}
        className="cursor-pointer rounded-sm border border-slate-700 px-3 py-1 text-emerald-300 transition hover:bg-slate-800 disabled:opacity-50"
      >
        {exporting ? "Exporting…" : "Export standings (CSV)"}
      </button>
      <button
        type="button"
        onClick={onExportSolutions}
        disabled={exportingSolutions}
        title="Every submitted solution as .java files per student and problem, plus index.csv"
        className="cursor-pointer rounded-sm border border-slate-700 px-3 py-1 text-emerald-300 transition hover:bg-slate-800 disabled:opacity-50"
      >
        {exportingSolutions ? "Preparing…" : "Download solutions (ZIP)"}
      </button>
      <button
        type="button"
        onClick={onRequestRejudge}
        disabled={rejudgePending}
        className="cursor-pointer rounded-sm border border-slate-700 px-3 py-1 text-amber-300 transition hover:bg-slate-800 disabled:opacity-50"
      >
        Rejudge contest
      </button>
    </div>
  );
}
