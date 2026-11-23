export type IntegrityClientEventType =
  | "visibility_hidden"
  | "visibility_visible"
  | "window_blur"
  | "window_focus"
  | "editor_paste"
  | "fullscreen_exit"
  | "fullscreen_enter";

export const FOCUS_SOFT_BLOCK_THRESHOLD = 5;
export const PASTE_SOFT_BLOCK_THRESHOLD = 3;
/** Grace window before counting a tab hide in strict mode (filters OS/alt-tab flickers). */
export const VISIBILITY_GRACE_MS = 2_500;

export function shouldClientImmediateBlock(
  strict: boolean,
  eventType: IntegrityClientEventType,
): boolean {
  if (!strict) return false;
  return eventType === "fullscreen_exit";
}

export function formatFocusWarning(
  focusSinceAck: number,
  strict: boolean,
): string | null {
  if (!strict || focusSinceAck <= 0 || focusSinceAck >= FOCUS_SOFT_BLOCK_THRESHOLD) {
    return null;
  }
  return `Tab or window switch recorded (${focusSinceAck}/${FOCUS_SOFT_BLOCK_THRESHOLD} before Submit soft-blocks). Stay on this contest tab.`;
}
