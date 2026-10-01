// Code drafts in localStorage. Lab PCs are shared, so a draft is scoped to the
// user (and to practice vs. a specific contest) and wiped on logout.
const PREFIX = "draft:";

export function draftKey(userId: number, contestId: string | null, slug: string) {
  return `${PREFIX}${userId}:${contestId ?? "practice"}:${slug}`;
}

export function loadDraft(key: string): string | null {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}

export function saveDraft(key: string, code: string) {
  try {
    localStorage.setItem(key, code);
  } catch {
    // Storage full or blocked: drafts are a convenience only.
  }
}

/** Remove every draft, including legacy `draft:<slug>` keys from older builds. */
export function clearAllDrafts() {
  try {
    const keys: string[] = [];
    for (let i = 0; i < localStorage.length; i++) {
      const k = localStorage.key(i);
      if (k?.startsWith(PREFIX)) keys.push(k);
    }
    keys.forEach((k) => localStorage.removeItem(k));
  } catch {
    // ignore
  }
}
