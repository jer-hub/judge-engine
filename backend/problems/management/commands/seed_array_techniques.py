"""Seed the "Java Array Technique Recognition" problem set.

Ten problems, each built so a student meets one array technique for the
first time and learns to recognise it: prefix sum, difference array, two
pointers, fixed and variable sliding window, binary search on the answer,
Kadane, frequency array, coordinate compression and sparse table.

Hidden tests are generated with fixed seeds, so every run produces the same
data, and expected outputs come from the reference solvers below. Each set
includes a large case (n around 10^5) that the naive approach cannot finish
within the time limit, which is what makes the technique necessary.

    python manage.py seed_array_techniques            # create or update
    python manage.py seed_array_techniques --draft    # leave unpublished
"""
from __future__ import annotations

import bisect
import random
from collections import Counter
from dataclasses import dataclass, field
from typing import Callable

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from problems.models import Problem, TestCase

User = get_user_model()
TAG = "array-techniques"


# --- reference solvers: parse the exact input text, return the expected output


def _ints(text: str) -> list[int]:
    return [int(x) for x in text.split()]


def solve_ledger(inp: str) -> str:
    t = _ints(inp)
    n = t[0]
    a = t[1 : 1 + n]
    pref = [0]
    for x in a:
        pref.append(pref[-1] + x)
    q = t[1 + n]
    qs = t[2 + n :]
    return "\n".join(str(pref[qs[2 * i + 1] + 1] - pref[qs[2 * i]]) for i in range(q)) + "\n"


def solve_coffee(inp: str) -> str:
    t = _ints(inp)
    n, u = t[0], t[1]
    diff = [0] * (n + 1)
    for i in range(u):
        l, r, v = t[2 + 3 * i : 5 + 3 * i]
        diff[l] += v
        diff[r + 1] -= v
    out, running = [], 0
    for i in range(n):
        running += diff[i]
        out.append(str(running))
    return " ".join(out) + "\n"


def solve_pair(inp: str) -> str:
    t = _ints(inp)
    n = t[0]
    a = t[1 : 1 + n]
    target = t[1 + n]
    l, r = 0, n - 1
    while l < r:
        s = a[l] + a[r]
        if s == target:
            return f"{l} {r}\n"
        if s < target:
            l += 1
        else:
            r -= 1
    return "-1 -1\n"


def solve_hottest(inp: str) -> str:
    t = _ints(inp)
    n, k = t[0], t[1]
    a = t[2 : 2 + n]
    s = sum(a[:k])
    best = s
    for i in range(k, n):
        s += a[i] - a[i - k]
        best = max(best, s)
    return f"{best}\n"


def solve_budget(inp: str) -> str:
    t = _ints(inp)
    n, cap = t[0], t[1]
    a = t[2 : 2 + n]
    left = best = s = 0
    for right in range(n):
        s += a[right]
        while s > cap:
            s -= a[left]
            left += 1
        best = max(best, right - left + 1)
    return f"{best}\n"


def solve_printer(inp: str) -> str:
    t = _ints(inp)
    n, h = t[0], t[1]
    pages = t[2 : 2 + n]

    def can_finish(speed: int) -> bool:
        return sum((p + speed - 1) // speed for p in pages) <= h

    lo, hi = 1, max(pages)
    while lo < hi:
        mid = (lo + hi) // 2
        if can_finish(mid):
            hi = mid
        else:
            lo = mid + 1
    return f"{lo}\n"


def solve_kadane(inp: str) -> str:
    t = _ints(inp)
    a = t[1 : 1 + t[0]]
    cur = best = a[0]
    for x in a[1:]:
        cur = max(x, cur + x)
        best = max(best, cur)
    return f"{best}\n"


def solve_anagram(inp: str) -> str:
    s, t = inp.split()
    return "YES\n" if len(s) == len(t) and Counter(s) == Counter(t) else "NO\n"


def solve_ranking(inp: str) -> str:
    t = _ints(inp)
    a = t[1 : 1 + t[0]]
    distinct = sorted(set(a))
    return " ".join(str(bisect.bisect_left(distinct, x)) for x in a) + "\n"


def solve_coldest(inp: str) -> str:
    t = _ints(inp)
    n = t[0]
    a = t[1 : 1 + n]
    table = [a]
    k = 1
    while (1 << k) <= n:
        prev, half = table[-1], 1 << (k - 1)
        table.append([min(prev[i], prev[i + half]) for i in range(n - (1 << k) + 1)])
        k += 1
    q = t[1 + n]
    qs = t[2 + n :]
    out = []
    for i in range(q):
        l, r = qs[2 * i], qs[2 * i + 1]
        j = (r - l + 1).bit_length() - 1
        out.append(str(min(table[j][l], table[j][r - (1 << j) + 1])))
    return "\n".join(out) + "\n"


# --- input builders and generators


def _line(values) -> str:
    return " ".join(str(v) for v in values)


def ledger_input(a, queries) -> str:
    rows = "\n".join(f"{l} {r}" for l, r in queries)
    return f"{len(a)}\n{_line(a)}\n{len(queries)}\n{rows}\n"


def coffee_input(n, promos) -> str:
    rows = "\n".join(f"{l} {r} {v}" for l, r, v in promos)
    return f"{n} {len(promos)}\n{rows}\n"


def pair_input(a, target) -> str:
    return f"{len(a)}\n{_line(a)}\n{target}\n"


def nk_input(first, second, a) -> str:
    return f"{first} {second}\n{_line(a)}\n"


def n_input(a) -> str:
    return f"{len(a)}\n{_line(a)}\n"


def _ranges(rng, n, q, long_ranges=False):
    out = []
    for _ in range(q):
        if long_ranges:
            l = rng.randrange(0, max(1, n // 10))
            r = rng.randrange(max(l, n - n // 10 - 1), n)
        else:
            l = rng.randrange(n)
            r = rng.randrange(l, n)
        out.append((l, r))
    return out


def _unique_pair_array(rng, n, with_pair: bool):
    """Sorted, distinct values where at most one pair sums to the target.

    Every value is 0 mod 4 except one that is 1 mod 4 and one that is 2 mod 4.
    The target is 3 mod 4, and only 1 + 2 reaches 3 mod 4, so the special
    pair is the only possible answer. Values stay in [0, 10^9]."""
    base = rng.sample(range(0, 250_000_000), n - 2)
    values = [4 * x for x in base]
    x = 4 * rng.randrange(0, 250_000_000) + 1
    y = 4 * rng.randrange(0, 250_000_000) + 2
    values += [x, y]
    values.sort()
    target = x + y if with_pair else x + y + 4
    return values, target


# Measured: Scanner + println alone takes 2-6 s on these inputs, even with
# the right technique, so the statement says how to read and write fast.
FAST_IO_NOTE = (
    "\n### Fast input and output\n"
    "The input can have hundreds of thousands of numbers. `Scanner` and one "
    "`System.out.println` per answer are too slow for that, even with the right "
    "technique. Read with `BufferedReader` + `StringTokenizer`, collect the output "
    "in a `StringBuilder`, and print it once at the end.\n"
)


@dataclass
class Spec:
    slug: str
    title: str
    difficulty: str
    tags: str
    story: str
    input_md: str
    output_md: str
    constraints_md: str
    hint: str
    solve: Callable[[str], str]
    sample: str
    hidden: list[str] = field(default_factory=list)
    time_limit_ms: int = 2000
    fast_io: bool = False

    def statement(self) -> str:
        sample_out = self.solve(self.sample)
        return (
            f"# {self.title}\n\n{self.story}\n\n"
            f"### Input\n{self.input_md}\n\n"
            f"### Output\n{self.output_md}\n\n"
            f"### Constraints\n{self.constraints_md}\n\n"
            f"### Sample\n**Input**\n```\n{self.sample}```\n"
            f"**Output**\n```\n{sample_out}```\n\n"
            f"### Hint\n{self.hint}\n"
            + (FAST_IO_NOTE if self.fast_io else "")
        )


def build_specs() -> list[Spec]:
    specs = []

    # 1. Prefix sum
    rng = random.Random(1001)
    big = [rng.randint(0, 10_000) for _ in range(100_000)]
    specs.append(Spec(
        slug="library-ledger",
        title="The Library Ledger",
        difficulty=Problem.Difficulty.EASY,
        tags=f"{TAG},prefix-sum",
        story=(
            "A librarian records how many books are borrowed each day for `n` days. "
            "Visitors keep asking: *\"How many books were borrowed from day L to day R?\"* "
            "The librarian is tired of recounting every time."
        ),
        input_md=(
            "- Line 1: `n`, the number of days\n"
            "- Line 2: `n` integers `a[0..n-1]`, books borrowed each day\n"
            "- Line 3: `q`, the number of queries\n"
            "- Next `q` lines: `L R` (0-indexed, inclusive)"
        ),
        output_md="For each query, print the total number of books borrowed from day `L` to day `R`, one per line.",
        constraints_md="- `1 ≤ n, q ≤ 10^5`\n- `0 ≤ a[i] ≤ 10^4`\n- `0 ≤ L ≤ R < n`",
        hint=(
            "Answering every query with a loop is O(n·q), which is too slow. "
            "Precompute cumulative sums once."
        ),
        solve=solve_ledger,
        time_limit_ms=3000,
        fast_io=True,
        sample=ledger_input([3, 1, 4, 1, 5], [(0, 2), (1, 3), (0, 4)]),
        hidden=[
            ledger_input([7], [(0, 0)]),
            ledger_input([0, 0, 0, 0], [(0, 3), (1, 2)]),
            ledger_input([rng.randint(0, 10_000) for _ in range(50)], _ranges(rng, 50, 30)),
            ledger_input([10_000] * 1000, _ranges(rng, 1000, 500)),
            ledger_input(big, _ranges(rng, 100_000, 100_000, long_ranges=True)),
        ],
    ))

    # 2. Difference array
    rng = random.Random(1002)
    specs.append(Spec(
        slug="coffee-machine",
        title="The Coffee Machine",
        difficulty=Problem.Difficulty.EASY,
        tags=f"{TAG},difference-array",
        story=(
            "A coffee machine gives free refills. The manager runs several promotions: "
            "*\"From day L to day R, add V extra cups per day.\"* After all promotions, "
            "the manager wants the total number of extra cups for each day. Every day starts at 0."
        ),
        input_md=(
            "- Line 1: `n u`, the number of days and the number of promotions\n"
            "- Next `u` lines: `L R V` (0-indexed, inclusive)"
        ),
        output_md="One line with `n` integers: the total for each day, separated by spaces.",
        constraints_md="- `1 ≤ n, u ≤ 10^5`\n- `0 ≤ L ≤ R < n`\n- `0 ≤ V ≤ 10^4`",
        hint=(
            "Applying each promotion day by day is O(n·u). Record only where each "
            "promotion *starts* and where it *stops*."
        ),
        solve=solve_coffee,
        fast_io=True,
        sample=coffee_input(5, [(0, 2, 3), (1, 4, 2), (2, 2, 5)]),
        hidden=[
            coffee_input(1, [(0, 0, 9)]),
            coffee_input(6, [(0, 5, 0), (5, 5, 10_000)]),
            coffee_input(40, [(*sorted((rng.randrange(40), rng.randrange(40))), rng.randint(0, 10_000)) for _ in range(25)]),
            coffee_input(100_000, [(0, 99_999, 10_000)] * 1000),
            coffee_input(
                100_000,
                [(rng.randrange(0, 10_000), rng.randrange(90_000, 100_000), rng.randint(0, 10_000))
                 for _ in range(100_000)],
            ),
        ],
    ))

    # 3. Two pointers
    rng = random.Random(1003)
    big_yes = _unique_pair_array(rng, 100_000, True)
    big_no = _unique_pair_array(rng, 100_000, False)
    mid_yes = _unique_pair_array(rng, 1000, True)
    specs.append(Spec(
        slug="balanced-pair",
        title="The Balanced Pair",
        difficulty=Problem.Difficulty.MEDIUM,
        tags=f"{TAG},two-pointers",
        story=(
            "A teacher has her students' exam scores, sorted from lowest to highest. "
            "She wants to find **two students whose scores add up exactly to a target**."
        ),
        input_md=(
            "- Line 1: `n`, the number of students\n"
            "- Line 2: `n` integers `a[0..n-1]`, sorted in ascending order\n"
            "- Line 3: `target`, the desired sum"
        ),
        output_md=(
            "Two indices `i j` with `i < j` and `a[i] + a[j] = target`, or `-1 -1` if no such pair exists. "
            "The tests guarantee there is **at most one** such pair."
        ),
        constraints_md=(
            "- `2 ≤ n ≤ 10^5`\n- `0 ≤ a[i] ≤ 10^9`, sorted ascending\n- `0 ≤ target ≤ 2·10^9`"
        ),
        hint=(
            "The array is sorted, so don't try every pair. Start with one pointer at each end "
            "and move them toward each other."
        ),
        solve=solve_pair,
        sample=pair_input([10, 25, 40, 55, 90], 100),
        hidden=[
            pair_input([1, 2], 3),
            pair_input([1, 2], 4),
            pair_input([5, 20, 30, 70, 85], 100),
            pair_input([0, 0], 0),
            pair_input(*mid_yes),
            pair_input(*big_yes),
            pair_input(*big_no),
        ],
    ))

    # 4. Fixed sliding window
    rng = random.Random(1004)
    big = [rng.randint(-10_000, 10_000) for _ in range(100_000)]
    specs.append(Spec(
        slug="hottest-week",
        title="The Hottest Week",
        difficulty=Problem.Difficulty.EASY,
        tags=f"{TAG},sliding-window",
        story=(
            "A weather station records the temperature for `n` days. Find the "
            "**maximum total temperature** over any `k` consecutive days."
        ),
        input_md="- Line 1: `n k`\n- Line 2: `n` integers `a[0..n-1]`",
        output_md="The maximum sum of any `k` consecutive values.",
        constraints_md="- `1 ≤ k ≤ n ≤ 10^5`\n- `-10^4 ≤ a[i] ≤ 10^4`",
        hint=(
            "Don't add up each window from scratch. Slide the window: add the new day "
            "and subtract the one that drops out."
        ),
        solve=solve_hottest,
        sample=nk_input(7, 3, [2, -1, 5, 4, -3, 6, 1]),
        hidden=[
            nk_input(1, 1, [-7]),
            nk_input(5, 5, [1, 2, 3, 4, 5]),
            nk_input(6, 2, [-5, -1, -8, -2, -9, -3]),
            nk_input(200, 17, [rng.randint(-10_000, 10_000) for _ in range(200)]),
            nk_input(100_000, 50_000, big),
            nk_input(100_000, 1, big),
        ],
    ))

    # 5. Variable sliding window
    rng = random.Random(1005)
    big = [rng.randint(0, 10_000) for _ in range(100_000)]
    specs.append(Spec(
        slug="budget-streak",
        title="The Budget Streak",
        difficulty=Problem.Difficulty.MEDIUM,
        tags=f"{TAG},sliding-window",
        story=(
            "A student tracks his daily expenses. He wants the **longest streak of consecutive days** "
            "whose total expense does not exceed his budget `S`."
        ),
        input_md="- Line 1: `n S`\n- Line 2: `n` integers `a[0..n-1]`, all non-negative",
        output_md="The length of the longest such streak (0 if no single day fits the budget).",
        constraints_md="- `1 ≤ n ≤ 10^5`\n- `0 ≤ a[i] ≤ 10^4`\n- `0 ≤ S ≤ 10^9`",
        hint="Grow the window with `r`, and shrink it from `l` while its sum is above `S`.",
        solve=solve_budget,
        sample=nk_input(6, 10, [4, 2, 3, 7, 1, 1]),
        hidden=[
            nk_input(1, 0, [5]),
            nk_input(1, 5, [5]),
            nk_input(5, 0, [0, 0, 3, 0, 0]),
            nk_input(300, 5000, [rng.randint(0, 10_000) for _ in range(300)]),
            nk_input(100_000, 1_000_000_000, big),
            nk_input(100_000, 250_000_000, big),
            nk_input(100_000, 2_000_000, big),
        ],
    ))

    # 6. Binary search on the answer
    rng = random.Random(1006)
    big = [rng.randint(1, 1_000_000_000) for _ in range(100_000)]
    specs.append(Spec(
        slug="slow-printer",
        title="The Slow Printer",
        difficulty=Problem.Difficulty.MEDIUM,
        tags=f"{TAG},binary-search",
        story=(
            "A printer prints `x` pages per hour. It must finish `n` print jobs within `h` hours. "
            "It works on one job at a time, and if a job finishes partway through an hour, the rest "
            "of that hour is wasted. Find the **minimum speed `x`** that finishes every job in time."
        ),
        input_md="- Line 1: `n h`\n- Line 2: `n` integers `pages[0..n-1]`",
        output_md="The minimum feasible speed `x`.",
        constraints_md="- `1 ≤ n ≤ 10^5`\n- `n ≤ h ≤ 10^9`\n- `1 ≤ pages[i] ≤ 10^9`",
        hint=(
            "\"Can every job finish in `h` hours at speed `x`?\" is monotonic in `x`: once it is true, "
            "it stays true for faster speeds. Binary search on `x`."
        ),
        solve=solve_printer,
        sample=nk_input(4, 8, [3, 6, 7, 11]),
        hidden=[
            nk_input(1, 1, [1]),
            nk_input(1, 1_000_000_000, [1_000_000_000]),
            nk_input(5, 5, [30, 11, 23, 4, 20]),
            nk_input(5, 6, [30, 11, 23, 4, 20]),
            nk_input(100_000, 100_000, big),
            nk_input(100_000, 999_999_999, big),
            nk_input(100_000, 1_234_567, big),
        ],
    ))

    # 7. Kadane
    rng = random.Random(1007)
    specs.append(Spec(
        slug="lucky-stretch",
        title="The Lucky Stretch",
        difficulty=Problem.Difficulty.EASY,
        tags=f"{TAG},kadane",
        story=(
            "A stock trader records each day's profit or loss. Find the **stretch of consecutive days** "
            "with the **largest total profit**. The stretch must contain at least one day."
        ),
        input_md="- Line 1: `n`\n- Line 2: `n` integers `a[0..n-1]` (may be negative)",
        output_md="The maximum sum of a non-empty contiguous subarray.",
        constraints_md="- `1 ≤ n ≤ 10^5`\n- `-10^4 ≤ a[i] ≤ 10^4`",
        hint="At each day, decide: extend the stretch that ended yesterday, or start fresh today.",
        solve=solve_kadane,
        sample=n_input([-2, 1, -3, 4, -1, 2, 1, -5, 4]),
        hidden=[
            n_input([-9]),
            n_input([-3, -1, -7, -2]),
            n_input([5, 4, -1, 7, 8]),
            n_input([rng.randint(-10_000, 10_000) for _ in range(500)]),
            n_input([rng.randint(-10_000, 10_000) for _ in range(100_000)]),
            n_input([rng.randint(-10_000, 9_000) for _ in range(100_000)]),
        ],
    ))

    # 8. Frequency array
    rng = random.Random(1008)
    letters = "abcdefghijklmnopqrstuvwxyz"
    big = "".join(rng.choice(letters) for _ in range(1_000_000))
    big_shuffled = list(big)
    rng.shuffle(big_shuffled)
    big_shuffled = "".join(big_shuffled)
    almost = big_shuffled[:-1] + ("a" if big_shuffled[-1] != "a" else "b")
    specs.append(Spec(
        slug="letter-detective",
        title="The Letter Detective",
        difficulty=Problem.Difficulty.EASY,
        tags=f"{TAG},frequency-array",
        story=(
            "Two students want to know whether two words are **anagrams**: whether the letters of one "
            "can be rearranged to spell the other."
        ),
        input_md="- Line 1: string `s`\n- Line 2: string `t`\n\nBoth contain only lowercase letters `a`–`z`.",
        output_md="`YES` if `s` and `t` are anagrams, otherwise `NO`.",
        constraints_md="- `1 ≤ |s|, |t| ≤ 10^6`",
        hint="Count how many times each letter appears in each string. The counts must match exactly.",
        solve=solve_anagram,
        sample="listen\nsilent\n",
        hidden=[
            "a\na\n",
            "ab\nabc\n",
            "aab\nabb\n",
            "racecar\ncarrace\n",
            f"{big}\n{big_shuffled}\n",
            f"{big}\n{almost}\n",
        ],
    ))

    # 9. Coordinate compression
    rng = random.Random(1009)
    specs.append(Spec(
        slug="ranking-game",
        title="The Ranking Game",
        difficulty=Problem.Difficulty.MEDIUM,
        tags=f"{TAG},coordinate-compression",
        story=(
            "A contest gives scores that can be **very large** (up to 10^9 in size). Give each contestant a "
            "**rank**: 0 for the smallest score, 1 for the next distinct score, and so on. "
            "Contestants with the same score get the same rank."
        ),
        input_md="- Line 1: `n`\n- Line 2: `n` integers `a[0..n-1]`",
        output_md="One line with each contestant's rank, in input order, separated by spaces.",
        constraints_md="- `1 ≤ n ≤ 10^5`\n- `-10^9 ≤ a[i] ≤ 10^9`",
        hint=(
            "You can't make an array with 10^9 slots, but you can **map the large values to small ranks** "
            "while keeping their order: sort, remove duplicates, then look each value up."
        ),
        solve=solve_ranking,
        fast_io=True,
        sample=n_input([100, -5, 100, 1_000_000_000, 7]),
        hidden=[
            n_input([42]),
            n_input([3, 3, 3]),
            n_input([-1_000_000_000, 1_000_000_000, 0]),
            n_input([rng.randint(-50, 50) for _ in range(200)]),
            n_input([rng.randint(-1_000_000_000, 1_000_000_000) for _ in range(100_000)]),
            n_input([rng.randint(-1000, 1000) for _ in range(100_000)]),
        ],
    ))

    # 10. Sparse table
    rng = random.Random(1010)
    big = [rng.randint(-1_000_000_000, 1_000_000_000) for _ in range(100_000)]
    specs.append(Spec(
        slug="coldest-window",
        title="The Coldest Window",
        difficulty=Problem.Difficulty.HARD,
        tags=f"{TAG},sparse-table",
        story=(
            "A weather scientist records each day's minimum temperature. She asks many questions: "
            "*\"What was the lowest temperature between day L and day R?\"* The recorded data never changes."
        ),
        input_md=(
            "- Line 1: `n`\n- Line 2: `n` integers `a[0..n-1]`\n- Line 3: `q`\n"
            "- Next `q` lines: `L R` (0-indexed, inclusive)"
        ),
        output_md="For each query, print the minimum of `a[L..R]`, one per line.",
        constraints_md="- `1 ≤ n, q ≤ 10^5`\n- `-10^9 ≤ a[i] ≤ 10^9`\n- `0 ≤ L ≤ R < n`",
        hint=(
            "The array never changes and there are many range-minimum queries. Precompute a "
            "**sparse table** (the minimum of every block whose length is a power of two) so each "
            "query takes O(1)."
        ),
        solve=solve_coldest,
        time_limit_ms=3000,
        fast_io=True,
        sample=ledger_input([5, 2, 8, -1, 3, 7], [(0, 2), (2, 5), (4, 4), (0, 5)]),
        hidden=[
            ledger_input([-7], [(0, 0)]),
            ledger_input([4, 4, 4, 4], [(0, 3), (1, 2), (3, 3)]),
            ledger_input([rng.randint(-100, 100) for _ in range(64)], _ranges(rng, 64, 64)),
            ledger_input(big, _ranges(rng, 100_000, 100_000, long_ranges=True)),
            ledger_input(big, _ranges(rng, 100_000, 100_000)),
        ],
    ))

    return specs


class Command(BaseCommand):
    help = "Create or update the Java array-technique problem set (10 problems)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--draft", action="store_true",
            help="Leave the problems unpublished (students cannot see them yet).",
        )

    def handle(self, *args, **options):
        owner = (
            User.objects.filter(is_superuser=True).order_by("id").first()
            or User.objects.filter(role=User.Role.ADMIN).order_by("id").first()
        )
        for spec in build_specs():
            with transaction.atomic():
                problem, created = Problem.objects.update_or_create(
                    slug=spec.slug,
                    defaults={
                        "title": spec.title,
                        "statement": spec.statement(),
                        "difficulty": spec.difficulty,
                        "tags": spec.tags,
                        "is_published": not options["draft"],
                        "time_limit_ms": spec.time_limit_ms,
                        "memory_limit_mb": 256,
                        "created_by": owner,
                    },
                )
                problem.test_cases.all().delete()
                cases = [(True, spec.sample)] + [(False, inp) for inp in spec.hidden]
                for order, (is_sample, inp) in enumerate(cases, start=1):
                    TestCase.objects.create(
                        problem=problem,
                        order=order,
                        is_sample=is_sample,
                        input_data=inp,
                        expected_output=spec.solve(inp),
                    )
            self.stdout.write(self.style.SUCCESS(
                f"{'Created' if created else 'Updated'} {spec.slug} ({len(cases)} tests)"
            ))
