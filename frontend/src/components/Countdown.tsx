"use client";

import { useEffect, useRef, useState } from "react";

type Props = {
  startTime: string;
  endTime: string;
  serverTime?: string;
  /** Called when the contest starts or ends while the page is open. */
  onPhaseChange?: () => void;
};

type Phase = "upcoming" | "active" | "ended";

export function Countdown({ startTime, endTime, serverTime, onPhaseChange }: Props) {
  // Server clock minus this device's clock, fixed when the server time arrives.
  // Reading Date.now() each tick (instead of adding 1 s per tick) keeps the
  // countdown right even when a background tab's timers are throttled.
  const [offset, setOffset] = useState(0);
  useEffect(() => {
    setOffset(serverTime ? new Date(serverTime).getTime() - Date.now() : 0);
  }, [serverTime]);

  const [now, setNow] = useState(() => Date.now() + offset);
  useEffect(() => {
    const update = () => setNow(Date.now() + offset);
    update();
    const tick = setInterval(update, 1000);
    return () => clearInterval(tick);
  }, [offset]);

  const start = new Date(startTime).getTime();
  const end = new Date(endTime).getTime();
  const phase: Phase = now < start ? "upcoming" : now <= end ? "active" : "ended";

  const lastPhase = useRef(phase);
  useEffect(() => {
    if (lastPhase.current !== phase) {
      lastPhase.current = phase;
      onPhaseChange?.();
    }
  }, [phase, onPhaseChange]);

  let label = "";
  let remaining = 0;
  if (phase === "upcoming") {
    label = "Starts in";
    remaining = start - now;
  } else if (phase === "active") {
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
