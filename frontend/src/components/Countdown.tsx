"use client";

import { useEffect, useState } from "react";

type Props = {
  startTime: string;
  endTime: string;
  serverTime?: string;
};

export function Countdown({ startTime, endTime, serverTime }: Props) {
  const [now, setNow] = useState(() =>
    serverTime ? new Date(serverTime).getTime() : Date.now(),
  );

  useEffect(() => {
    const tick = setInterval(() => setNow((t) => t + 1000), 1000);
    return () => clearInterval(tick);
  }, []);

  const start = new Date(startTime).getTime();
  const end = new Date(endTime).getTime();

  let label = "";
  let remaining = 0;
  if (now < start) {
    label = "Starts in";
    remaining = start - now;
  } else if (now <= end) {
    label = "Ends in";
    remaining = end - now;
  } else {
    label = "Contest ended";
    remaining = 0;
  }

  return (
    <div className="rounded-lg border border-slate-800 bg-slate-900/60 px-4 py-3">
      <div className="text-xs uppercase tracking-wide text-slate-400">{label}</div>
      <div className="font-mono text-2xl text-emerald-300">
        {remaining > 0 ? formatDuration(remaining) : "—"}
      </div>
    </div>
  );
}

function formatDuration(ms: number) {
  const total = Math.max(0, Math.floor(ms / 1000));
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  return [h, m, s].map((n) => String(n).padStart(2, "0")).join(":");
}
