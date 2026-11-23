"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { apiFetch } from "@/lib/api";
import {
  type IntegrityClientEventType,
  VISIBILITY_GRACE_MS,
  formatFocusWarning,
  shouldClientImmediateBlock,
} from "@/lib/integrity";

type QueuedEvent = {
  type: IntegrityClientEventType;
  count: number;
  meta?: { chars?: number };
};

type EventsResponse = {
  created: number;
  integrity_blocked?: boolean;
  integrity_focus_since_ack?: number;
  integrity_paste_since_ack?: number;
};

const FLUSH_MS = 20_000;
const BANNER_KEY = (id: number) => `je-integrity-banner-${id}`;

function isFullscreen(): boolean {
  return typeof document !== "undefined" && !!document.fullscreenElement;
}

/**
 * Contest integrity: monitor (log-only) or strict (fullscreen + soft-block).
 */
export function useContestIntegrity(
  contestId: number | null,
  enabled: boolean,
  strict: boolean,
  initiallyBlocked = false,
): {
  notice: string | null;
  dismissNotice: () => void;
  focusWarning: string | null;
  dismissFocusWarning: () => void;
  recordPaste: (chars: number) => void;
  blocked: boolean;
  setBlocked: (v: boolean) => void;
  fullscreenOk: boolean;
  requestFullscreen: () => Promise<void>;
} {
  const queueRef = useRef<Map<string, QueuedEvent>>(new Map());
  const contestIdRef = useRef(contestId);
  const enabledRef = useRef(enabled);
  const strictRef = useRef(strict);
  contestIdRef.current = contestId;
  enabledRef.current = enabled;
  strictRef.current = strict;

  const [notice, setNotice] = useState<string | null>(null);
  const [focusWarning, setFocusWarning] = useState<string | null>(null);
  const [blocked, setBlockedState] = useState(initiallyBlocked);
  const [fullscreenOk, setFullscreenOk] = useState(() => !strict || isFullscreen());

  const setBlocked = useCallback((v: boolean) => {
    setBlockedState(v);
    if (!v) setFocusWarning(null);
  }, []);

  useEffect(() => {
    setBlocked(initiallyBlocked);
  }, [initiallyBlocked, contestId, setBlocked]);

  const enqueue = useCallback((type: IntegrityClientEventType, meta?: { chars?: number }) => {
    if (!enabledRef.current || !contestIdRef.current) return;
    const key =
      type === "editor_paste" || type === "fullscreen_exit" || type === "fullscreen_enter"
        ? `${type}-${Date.now()}-${Math.random()}`
        : type;
    const existing = queueRef.current.get(key);
    if (existing && type !== "editor_paste") {
      existing.count += 1;
      return;
    }
    queueRef.current.set(key, { type, count: 1, ...(meta ? { meta } : {}) });
  }, []);

  const flush = useCallback(async () => {
    const id = contestIdRef.current;
    if (!id || queueRef.current.size === 0) return;
    const events = Array.from(queueRef.current.values());
    queueRef.current.clear();
    for (let i = 0; i < events.length; i += 50) {
      const chunk = events.slice(i, i + 50);
      try {
        const res = await apiFetch<EventsResponse>(`/contests/${id}/integrity-events/`, {
          method: "POST",
          body: JSON.stringify({ events: chunk }),
        });
        if (res.integrity_blocked) {
          setBlockedState(true);
          setFocusWarning(null);
        } else if (typeof res.integrity_focus_since_ack === "number") {
          setFocusWarning(formatFocusWarning(res.integrity_focus_since_ack, strictRef.current));
        }
      } catch {
        // Silent: integrity telemetry must not break the editor.
      }
    }
  }, []);

  const requestFullscreen = useCallback(async () => {
    try {
      if (!document.fullscreenElement) {
        await document.documentElement.requestFullscreen();
      }
      setFullscreenOk(true);
      enqueue("fullscreen_enter");
      void flush();
    } catch {
      setFullscreenOk(false);
    }
  }, [enqueue, flush]);

  useEffect(() => {
    if (!enabled || !contestId) {
      setNotice(null);
      setFocusWarning(null);
      return;
    }

    if (typeof sessionStorage !== "undefined" && !sessionStorage.getItem(BANNER_KEY(contestId))) {
      setNotice(
        strict
          ? "Strict integrity: stay in fullscreen. Exiting fullscreen, repeated tab switches, or heavy pasting soft-blocks Submit until a teacher unlocks you."
          : "This contest logs tab focus and paste signals for teachers (review only — not auto-penalties).",
      );
    }

    let hideGraceTimer: number | null = null;
    const clearHideGrace = () => {
      if (hideGraceTimer !== null) {
        window.clearTimeout(hideGraceTimer);
        hideGraceTimer = null;
      }
    };

    const onVisibility = () => {
      if (document.visibilityState === "hidden") {
        if (strictRef.current) {
          clearHideGrace();
          hideGraceTimer = window.setTimeout(() => {
            hideGraceTimer = null;
            enqueue("visibility_hidden");
            void flush();
          }, VISIBILITY_GRACE_MS);
        } else {
          enqueue("visibility_hidden");
        }
      } else {
        clearHideGrace();
        enqueue("visibility_visible");
      }
    };
    const onBlur = () => {
      enqueue("window_blur");
    };
    const onFocus = () => enqueue("window_focus");
    const onFs = () => {
      if (document.fullscreenElement) {
        setFullscreenOk(true);
        enqueue("fullscreen_enter");
      } else {
        setFullscreenOk(false);
        enqueue("fullscreen_exit");
        if (shouldClientImmediateBlock(strictRef.current, "fullscreen_exit")) {
          setBlockedState(true);
          setFocusWarning(null);
          void flush();
        }
      }
    };

    document.addEventListener("visibilitychange", onVisibility);
    window.addEventListener("blur", onBlur);
    window.addEventListener("focus", onFocus);
    document.addEventListener("fullscreenchange", onFs);
    setFullscreenOk(!strict || isFullscreen());
    const timer = window.setInterval(() => void flush(), FLUSH_MS);

    return () => {
      clearHideGrace();
      document.removeEventListener("visibilitychange", onVisibility);
      window.removeEventListener("blur", onBlur);
      window.removeEventListener("focus", onFocus);
      document.removeEventListener("fullscreenchange", onFs);
      window.clearInterval(timer);
      void flush();
    };
  }, [contestId, enabled, strict, enqueue, flush]);

  const dismissNotice = useCallback(() => {
    if (contestId && typeof sessionStorage !== "undefined") {
      sessionStorage.setItem(BANNER_KEY(contestId), "1");
    }
    setNotice(null);
  }, [contestId]);

  const dismissFocusWarning = useCallback(() => {
    setFocusWarning(null);
  }, []);

  const recordPaste = useCallback(
    (chars: number) => {
      if (!enabledRef.current || !contestIdRef.current) return;
      enqueue("editor_paste", { chars: Math.max(0, Math.round(chars)) });
      if (strictRef.current) {
        void flush();
      }
    },
    [enqueue, flush],
  );

  return {
    notice,
    dismissNotice,
    focusWarning,
    dismissFocusWarning,
    recordPaste,
    blocked,
    setBlocked,
    fullscreenOk,
    requestFullscreen,
  };
}
