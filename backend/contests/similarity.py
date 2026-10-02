"""Code similarity between students' submissions (a MOSS-style winnowing).

A lead for a teacher to review, never proof: short solutions to an easy
problem legitimately look alike. Renaming variables, reformatting, and
editing comments do not hide copying, because the code is reduced to a
stream of token kinds before comparing.
"""
from __future__ import annotations

import re
import zlib
from collections import Counter
from itertools import combinations

from submissions.models import Submission

from .models import Contest

K = 5  # tokens per fingerprinted sequence
WINDOW = 4  # winnowing window: keeps one fingerprint per WINDOW sequences
MAX_PAIRS = 200
# After removing shared boilerplate, a program this small has too little
# left to compare meaningfully (a 2-of-3 overlap is not a signal).
MIN_FINGERPRINTS = 5

# The editor's starter code: every submission contains it.
JAVA_STUB = """import java.util.*;

public class Solution {
    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);

    }
}
"""

_JAVA_KEYWORDS = frozenset(
    """abstract assert boolean break byte case catch char class const continue default do
    double else enum extends final finally float for goto if implements import instanceof
    int interface long native new package private protected public return short static
    strictfp super switch synchronized this throw throws transient try void volatile while
    var record true false null""".split()
)

_TOKEN = re.compile(
    r"""
    (?P<comment>//[^\n]*|/\*.*?\*/)
  | (?P<string>"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*')
  | (?P<number>\b\d[\d_]*(?:\.\d+)?[lLfFdD]?\b)
  | (?P<word>[A-Za-z_$][\w$]*)
  | (?P<op>[^\s\w])
    """,
    re.VERBOSE | re.DOTALL,
)


def tokens(source: str) -> list[str]:
    """Java source as token kinds: keywords and operators kept, every name
    "I", every literal "L", comments and whitespace dropped."""
    out: list[str] = []
    for match in _TOKEN.finditer(source):
        kind = match.lastgroup
        if kind == "comment":
            continue
        if kind in ("string", "number"):
            out.append("L")
        elif kind == "word":
            word = match.group()
            out.append(word if word in _JAVA_KEYWORDS else "I")
        else:
            out.append(match.group())
    return out


def fingerprints(source: str) -> set[int]:
    """Winnowed hashes of every K-token sequence."""
    toks = tokens(source)
    if len(toks) < K:
        return {zlib.crc32(" ".join(toks).encode())} if toks else set()
    hashes = [zlib.crc32(" ".join(toks[i : i + K]).encode()) for i in range(len(toks) - K + 1)]
    if len(hashes) <= WINDOW:
        return {min(hashes)}
    return {min(hashes[i : i + WINDOW]) for i in range(len(hashes) - WINDOW + 1)}


def similarity(a: set[int], b: set[int]) -> float:
    """Share of the smaller program's fingerprints found in the other, so a
    copied solution padded with extra code still scores high."""
    if not a or not b:
        return 0.0
    return len(a & b) / min(len(a), len(b))


def _latest_per_student(contest: Contest, problem_id: int) -> list[Submission]:
    """Each student's last accepted submission, else their last one."""
    best: dict[int, Submission] = {}
    subs = (
        Submission.objects.filter(contest=contest, problem_id=problem_id)
        .exclude(status__in=[Submission.Status.COMPILE_ERROR, Submission.Status.SYSTEM_ERROR])
        .select_related("user")
        .order_by("submitted_at", "id")
    )
    for sub in subs:
        current = best.get(sub.user_id)
        accepted = sub.status == Submission.Status.ACCEPTED
        if current is None or accepted or current.status != Submission.Status.ACCEPTED:
            best[sub.user_id] = sub
    return list(best.values())


def contest_similarity(contest: Contest, threshold: float = 0.6) -> list[dict]:
    """Pairs of students per problem whose code is at least ``threshold``
    similar, most similar first (at most MAX_PAIRS)."""
    stub = fingerprints(JAVA_STUB)
    pairs: list[dict] = []
    for cp in contest.contest_problems.all():
        subs = _latest_per_student(contest, cp.problem_id)
        if len(subs) < 2:
            continue
        prints = {s.id: fingerprints(s.source_code) - stub for s in subs}
        # Fingerprints in most solutions are the problem's natural shape
        # (read input, loop, print), not evidence of copying.
        counts = Counter(fp for fps in prints.values() for fp in fps)
        common = {fp for fp, n in counts.items() if n > max(2, len(subs) // 2)}
        prints = {sid: fps - common for sid, fps in prints.items()}
        for a, b in combinations(subs, 2):
            if min(len(prints[a.id]), len(prints[b.id])) < MIN_FINGERPRINTS:
                continue
            score = similarity(prints[a.id], prints[b.id])
            if score >= threshold:
                pairs.append(
                    {
                        "problem_letter": cp.letter,
                        "score": round(score, 3),
                        "a": {"username": a.user.username, "submission_id": a.id, "status": a.status},
                        "b": {"username": b.user.username, "submission_id": b.id, "status": b.status},
                    }
                )
    pairs.sort(key=lambda p: p["score"], reverse=True)
    return pairs[:MAX_PAIRS]
