import { describe, expect, it } from "vitest";

import {
  FOCUS_SOFT_BLOCK_THRESHOLD,
  VISIBILITY_GRACE_MS,
  formatFocusWarning,
  shouldClientImmediateBlock,
} from "@/lib/integrity";

describe("strict integrity client policy", () => {
  it("only fullscreen_exit causes immediate client soft-block in strict mode", () => {
    expect(shouldClientImmediateBlock(true, "fullscreen_exit")).toBe(true);
    expect(shouldClientImmediateBlock(true, "visibility_hidden")).toBe(false);
    expect(shouldClientImmediateBlock(true, "window_blur")).toBe(false);
    expect(shouldClientImmediateBlock(false, "fullscreen_exit")).toBe(false);
  });

  it("defines a brief visibility grace window to filter OS/alt-tab flickers", () => {
    expect(VISIBILITY_GRACE_MS).toBeGreaterThanOrEqual(1500);
    expect(VISIBILITY_GRACE_MS).toBeLessThanOrEqual(5000);
  });

  it("formats focus warning message before threshold and clears when unlocked/zero", () => {
    expect(formatFocusWarning(0, true)).toBeNull();
    expect(formatFocusWarning(2, false)).toBeNull();
    const msg = formatFocusWarning(2, true);
    expect(msg).toContain(`2/${FOCUS_SOFT_BLOCK_THRESHOLD}`);
  });
});
