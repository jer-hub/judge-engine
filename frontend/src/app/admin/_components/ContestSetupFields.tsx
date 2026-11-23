"use client";

type Props = {
  title: string;
  onTitleChange: (v: string) => void;
  description: string;
  onDescriptionChange: (v: string) => void;
  startTime: string;
  onStartTimeChange: (v: string) => void;
  endTime: string;
  onEndTimeChange: (v: string) => void;
  durationLabel: string | null;
  onApplyDurationHours: (hours: number) => void;
  freeze: number;
  onFreezeChange: (v: number) => void;
  isPublic: boolean;
  onIsPublicChange: (v: boolean) => void;
  holdResults: boolean;
  onHoldResultsChange: (v: boolean) => void;
  practiceAfterEnd: boolean;
  onPracticeAfterEndChange: (v: boolean) => void;
  integrityMonitoring: boolean;
  onIntegrityMonitoringChange: (v: boolean) => void;
  integrityStrict: boolean;
  onIntegrityStrictChange: (v: boolean) => void;
};

export function ContestSetupFields({
  title,
  onTitleChange,
  description,
  onDescriptionChange,
  startTime,
  onStartTimeChange,
  endTime,
  onEndTimeChange,
  durationLabel,
  onApplyDurationHours,
  freeze,
  onFreezeChange,
  isPublic,
  onIsPublicChange,
  holdResults,
  onHoldResultsChange,
  practiceAfterEnd,
  onPracticeAfterEndChange,
  integrityMonitoring,
  onIntegrityMonitoringChange,
  integrityStrict,
  onIntegrityStrictChange,
}: Props) {
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      <label className="block text-sm sm:col-span-2">
        <span className="mb-1 block text-slate-400">Title</span>
        <input
          className="w-full rounded-sm border border-slate-700 bg-slate-900 px-3 py-2"
          value={title}
          onChange={(e) => onTitleChange(e.target.value)}
          required
        />
      </label>
      <label className="block text-sm sm:col-span-2">
        <span className="mb-1 block text-slate-400">Description</span>
        <textarea
          className="min-h-[72px] w-full rounded-sm border border-slate-700 bg-slate-900 px-3 py-2 text-sm"
          value={description}
          onChange={(e) => onDescriptionChange(e.target.value)}
        />
      </label>
      <label className="block text-sm">
        <span className="mb-1 block text-slate-400">Start</span>
        <input
          type="datetime-local"
          className="w-full rounded-sm border border-slate-700 bg-slate-900 px-3 py-2"
          value={startTime}
          onChange={(e) => onStartTimeChange(e.target.value)}
          required
        />
      </label>
      <label className="block text-sm">
        <span className="mb-1 flex flex-wrap items-center justify-between gap-2 text-slate-400">
          <span>End</span>
          {durationLabel && (
            <span className="text-xs text-slate-500">Duration {durationLabel}</span>
          )}
        </span>
        <input
          type="datetime-local"
          className="w-full rounded-sm border border-slate-700 bg-slate-900 px-3 py-2"
          value={endTime}
          onChange={(e) => onEndTimeChange(e.target.value)}
          required
        />
      </label>
      <div className="flex flex-wrap gap-2 sm:col-span-2">
        <span className="self-center text-xs text-slate-500">Length from start:</span>
        {[1, 2, 3].map((h) => (
          <button
            key={h}
            type="button"
            onClick={() => onApplyDurationHours(h)}
            aria-label={`Set contest length to ${h} hour${h === 1 ? "" : "s"} from start`}
            className="cursor-pointer rounded-sm border border-slate-700 px-2.5 py-1 text-xs text-slate-300 hover:bg-slate-800"
          >
            {h}h
          </button>
        ))}
      </div>
      <label className="block text-sm">
        <span className="mb-1 block text-slate-400">Freeze (min before end)</span>
        <input
          type="number"
          min={0}
          className="w-full rounded-sm border border-slate-700 bg-slate-900 px-3 py-2"
          value={freeze}
          onChange={(e) => onFreezeChange(Number(e.target.value))}
        />
        <span className="mt-1 block text-xs text-slate-500">
          0 = never freeze. 60 = hide new solves in the last hour.
        </span>
      </label>
      <label className="flex flex-col gap-1 self-end text-sm">
        <span className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={isPublic}
            onChange={(e) => onIsPublicChange(e.target.checked)}
            className="cursor-pointer"
          />
          <span>Public — anyone can see &amp; register</span>
        </span>
        <span className="text-xs text-slate-500">
          Uncheck for invite-only (use the participants list below).
        </span>
      </label>
      <label className="flex flex-col gap-1 text-sm sm:col-span-2">
        <span className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={holdResults}
            onChange={(e) => onHoldResultsChange(e.target.checked)}
            className="cursor-pointer"
          />
          <span>Keep the scoreboard frozen after the end until I reveal it</span>
        </span>
        <span className="text-xs text-slate-500">
          For an announcement, or while students with extra time are still working. Reveal below.
        </span>
      </label>
      <label className="flex flex-col gap-1 text-sm sm:col-span-2">
        <span className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={practiceAfterEnd}
            onChange={(e) => onPracticeAfterEndChange(e.target.checked)}
            className="cursor-pointer"
          />
          <span>Open its problems for practice after the contest</span>
        </span>
        <span className="text-xs text-slate-500">
          Leave off if you will reuse these problems. Practice stays closed while any contest
          using them is still running.
        </span>
      </label>
      <label className="flex flex-col gap-1 text-sm sm:col-span-2">
        <span className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={integrityMonitoring}
            onChange={(e) => onIntegrityMonitoringChange(e.target.checked)}
            className="cursor-pointer"
          />
          <span>Log integrity signals (focus / paste / submit IP)</span>
        </span>
        <span className="text-xs text-slate-500">
          Warn-only leads for teachers — never auto-penalizes. Students see a one-time notice.
        </span>
      </label>
      <label className="flex flex-col gap-1 text-sm sm:col-span-2">
        <span className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={integrityStrict}
            disabled={!integrityMonitoring}
            onChange={(e) => onIntegrityStrictChange(e.target.checked)}
            className="cursor-pointer"
          />
          <span>Strict: fullscreen + soft-block on exit or repeated switches</span>
        </span>
        <span className="text-xs text-slate-500">
          Requires fullscreen; exiting fullscreen, repeated tab switches, or heavy pasting
          soft-blocks Submit until unlocked in the Integrity panel. Requires monitoring on.
        </span>
      </label>
    </div>
  );
}
