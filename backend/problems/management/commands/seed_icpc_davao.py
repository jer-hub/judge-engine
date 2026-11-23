"""Seed the Davao Regional Java Programming Cup ICPC training set (10 problems).

Statements and visible samples come from `_icpc_davao_meta.json`. Expected
outputs are produced by the reference solvers below (never by shipping Java
editorials). Hidden tests use fixed RNG seeds.

    python manage.py seed_icpc_davao            # create or update, published
    python manage.py seed_icpc_davao --draft    # leave unpublished
"""
from __future__ import annotations

import heapq
import json
import random
from collections import defaultdict, deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from problems.models import Problem, TestCase

User = get_user_model()
TAG = "icpc-davao"
META_PATH = Path(__file__).with_name("_icpc_davao_meta.json")

SOLUTION_NOTE = (
    "\n### Submission format\n"
    "Submit a single Java file with `public class Solution` and a "
    "`public static void main(String[] args)` method. The judge compiles "
    "`Solution.java` (not `Main`).\n"
)

FAST_IO_NOTE = (
    "\n### Fast input and output\n"
    "Inputs can be large. Read with `BufferedReader` + `StringTokenizer` "
    "(or equivalent) and print from a `StringBuilder`; `Scanner` and one "
    "`println` per answer are often too slow.\n"
)


def _ints(text: str) -> list[int]:
    return [int(x) for x in text.split()]


def _ensure_nl(s: str) -> str:
    return s if s.endswith("\n") else s + "\n"


# --- A. Durian Stall Ledger -----------------------------------------------------------


def solve_durian(inp: str) -> str:
    t = _ints(inp)
    ti = 0
    days = t[ti]
    ti += 1
    out = []
    for _ in range(days):
        n = t[ti]
        ti += 1
        revenues = []
        total = 0
        for _ in range(n):
            k, p = t[ti], t[ti + 1]
            ti += 2
            r = k * p
            revenues.append(r)
            total += r
        best_i = 1
        best_r = revenues[0]
        for i, r in enumerate(revenues, 1):
            if r > best_r:
                best_r = r
                best_i = i
        # r > S/N  ⇔  r*N > S  (all non-negative)
        above = sum(1 for r in revenues if r * n > total)
        out.append(f"{total} {best_i} {above}")
    return "\n".join(out) + "\n"


# --- B. Jeepney Signboard Codes -------------------------------------------------------


def _encode_runs(s: str) -> str:
    parts: list[str] = []
    i, n = 0, len(s)
    while i < n:
        j = i + 1
        while j < n and s[j] == s[i]:
            j += 1
        length = j - i
        if length == 1:
            parts.append(s[i])
        else:
            parts.append(f"{s[i]}{length}")
        i = j
    return "".join(parts)


def _decode_runs(s: str) -> str:
    parts: list[str] = []
    i, n = 0, len(s)
    while i < n:
        c = s[i]
        i += 1
        if i < n and s[i].isdigit():
            j = i
            while j < n and s[j].isdigit():
                j += 1
            parts.append(c * int(s[i:j]))
            i = j
        else:
            parts.append(c)
    return "".join(parts)


def solve_jeepney(inp: str) -> str:
    lines = inp.splitlines()
    t = int(lines[0])
    out = []
    for k in range(1, t + 1):
        op, x = lines[k].split(maxsplit=1)
        out.append(_encode_runs(x) if op == "E" else _decode_runs(x))
    return "\n".join(out) + "\n"


# --- C. Cooperative Ledger Periods (subarray sum == K) --------------------------------


def solve_cooperative(inp: str) -> str:
    t = _ints(inp)
    n, k = t[0], t[1]
    a = t[2 : 2 + n]
    freq: dict[int, int] = defaultdict(int)
    freq[0] = 1
    first = {0: 0}
    pref = count = max_len = 0
    for j, x in enumerate(a, 1):
        pref += x
        need = pref - k
        count += freq[need]
        if need in first:
            max_len = max(max_len, j - first[need])
        freq[pref] += 1
        if pref not in first:
            first[pref] = j
    return f"{count} {max_len}\n"


# --- D. Kadayawan Cup Scoreboard ------------------------------------------------------


def solve_scoreboard(inp: str) -> str:
    lines = inp.splitlines()
    n, p, m = map(int, lines[0].split())
    teams = lines[1 : 1 + n]
    # per team: problem -> list of (time, verdict) already in order via log
    attempts: dict[str, dict[str, list[tuple[int, str]]]] = {
        name: {chr(ord("A") + i): [] for i in range(p)} for name in teams
    }
    for line in lines[1 + n : 1 + n + m]:
        time_s, team, prob, verdict = line.split()
        attempts[team][prob].append((int(time_s), verdict))

    rows = []
    for name in teams:
        solved = penalty = 0
        for prob in attempts[name]:
            wa_before = 0
            for tm, verd in attempts[name][prob]:
                if verd == "CE":
                    continue
                if verd == "AC":
                    solved += 1
                    penalty += tm + 20 * wa_before
                    break
                if verd in ("WA", "TLE", "RTE"):
                    wa_before += 1
        rows.append((name, solved, penalty))

    # sort for display: more solved, less penalty, name
    rows.sort(key=lambda r: (-r[1], r[2], r[0]))
    # ranks: 1 + number of teams strictly better
    out = []
    for name, solved, penalty in rows:
        better = sum(1 for _, s2, p2 in rows if s2 > solved or (s2 == solved and p2 < penalty))
        out.append(f"{better + 1} {name} {solved} {penalty}")
    return "\n".join(out) + "\n"


# --- E. Samal Ferry -------------------------------------------------------------------


def _ferry_ok(weights: list[int], capacity: int, trips: int, seats: int) -> bool:
    i, n = 0, len(weights)
    used = 0
    while i < n:
        if used == trips:
            return False
        if weights[i] > capacity:
            return False
        load = 0
        taken = 0
        while i < n and taken < seats and load + weights[i] <= capacity:
            load += weights[i]
            taken += 1
            i += 1
        used += 1
    return True


def solve_ferry(inp: str) -> str:
    t = _ints(inp)
    ti = 0
    cases = t[ti]
    ti += 1
    out = []
    for _ in range(cases):
        n, k, p = t[ti], t[ti + 1], t[ti + 2]
        ti += 3
        w = t[ti : ti + n]
        ti += n
        # Impossible when even infinite capacity needs more than K trips.
        if (n + p - 1) // p > k:
            out.append("-1")
            continue
        lo = max(w)
        hi = sum(w)
        while lo < hi:
            mid = (lo + hi) // 2
            if _ferry_ok(w, mid, k, p):
                hi = mid
            else:
                lo = mid + 1
        out.append(str(lo))
    return "\n".join(out) + "\n"


# --- F. Flash Flood in Matina ---------------------------------------------------------


def solve_flood(inp: str) -> str:
    lines = inp.splitlines()
    t = int(lines[0])
    li = 1
    out = []
    dirs = ((1, 0), (-1, 0), (0, 1), (0, -1))
    for _ in range(t):
        r, c = map(int, lines[li].split())
        li += 1
        grid = lines[li : li + r]
        li += r
        water_q: deque[tuple[int, int]] = deque()
        water = [[-1] * c for _ in range(r)]
        sr = sc = -1
        exits: list[tuple[int, int]] = []
        for i in range(r):
            for j in range(c):
                ch = grid[i][j]
                if ch == "W":
                    water[i][j] = 0
                    water_q.append((i, j))
                elif ch == "S":
                    sr, sc = i, j
                elif ch == "E":
                    exits.append((i, j))
        while water_q:
            x, y = water_q.popleft()
            for dx, dy in dirs:
                nx, ny = x + dx, y + dy
                if 0 <= nx < r and 0 <= ny < c and water[nx][ny] < 0:
                    cell = grid[nx][ny]
                    if cell in ("#", "E"):
                        continue
                    water[nx][ny] = water[x][y] + 1
                    water_q.append((nx, ny))

        if not exits:
            out.append("TRAPPED")
            continue

        dist = [[-1] * c for _ in range(r)]
        dist[sr][sc] = 0
        jq: deque[tuple[int, int]] = deque([(sr, sc)])
        ans = None
        while jq:
            x, y = jq.popleft()
            tnow = dist[x][y]
            if grid[x][y] == "E":
                ans = tnow
                break
            for dx, dy in dirs:
                nx, ny = x + dx, y + dy
                if not (0 <= nx < r and 0 <= ny < c):
                    continue
                if dist[nx][ny] >= 0 or grid[nx][ny] == "#":
                    continue
                arrive = tnow + 1
                if grid[nx][ny] != "E":
                    wt = water[nx][ny]
                    if wt >= 0 and wt <= arrive:
                        continue
                dist[nx][ny] = arrive
                jq.append((nx, ny))
        out.append("TRAPPED" if ans is None else str(ans))
    return "\n".join(out) + "\n"


# --- G. Toll Passes over the Davao River ----------------------------------------------


def solve_toll(inp: str) -> str:
    t = _ints(inp)
    n, m, k = t[0], t[1], t[2]
    g: list[list[tuple[int, int]]] = [[] for _ in range(n + 1)]
    idx = 3
    for _ in range(m):
        u, v, w = t[idx], t[idx + 1], t[idx + 2]
        idx += 3
        g[u].append((v, w))
        g[v].append((u, w))
    # dist[node][passes_used]
    inf = 10**30
    dist = [[inf] * (k + 1) for _ in range(n + 1)]
    dist[1][0] = 0
    pq: list[tuple[int, int, int]] = [(0, 1, 0)]  # cost, node, used
    while pq:
        cost, u, used = heapq.heappop(pq)
        if cost != dist[u][used]:
            continue
        for v, w in g[u]:
            # pay
            if cost + w < dist[v][used]:
                dist[v][used] = cost + w
                heapq.heappush(pq, (cost + w, v, used))
            # free pass
            if used < k and cost < dist[v][used + 1]:
                dist[v][used + 1] = cost
                heapq.heappush(pq, (cost, v, used + 1))
    best = min(dist[n])
    return f"{-1 if best >= inf else best}\n"


# --- H. SMX Hall Bookings -------------------------------------------------------------


def solve_smx(inp: str) -> str:
    t = _ints(inp)
    n, g = t[0], t[1]
    jobs = []
    idx = 2
    for _ in range(n):
        s, e, p = t[idx], t[idx + 1], t[idx + 2]
        idx += 3
        jobs.append((e, s, p))
    jobs.sort()  # by end time
    ends = [e for e, _, _ in jobs]
    # dp[i] = best using jobs[0..i]
    dp = [0] * n
    for i, (e, s, p) in enumerate(jobs):
        # latest j with ends[j] + g <= s  ⇔  ends[j] <= s - g
        limit = s - g
        # binary search rightmost ends[j] <= limit
        lo, hi = 0, i
        best_j = -1
        while lo < hi:
            mid = (lo + hi) // 2
            if ends[mid] <= limit:
                best_j = mid
                lo = mid + 1
            else:
                hi = mid
        take = p + (dp[best_j] if best_j >= 0 else 0)
        skip = dp[i - 1] if i else 0
        dp[i] = max(skip, take)
    return f"{dp[-1] if n else 0}\n"


# --- I. Barangay Health Hub -----------------------------------------------------------


def solve_health(inp: str) -> str:
    t = _ints(inp)
    n = t[0]
    pop = t[1 : 1 + n]
    g: list[list[tuple[int, int]]] = [[] for _ in range(n + 1)]
    idx = 1 + n
    for _ in range(n - 1):
        u, v, w = t[idx], t[idx + 1], t[idx + 2]
        idx += 3
        g[u].append((v, w))
        g[v].append((u, w))
    if n == 1:
        return "0\n1\n"

    parent = [0] * (n + 1)
    order: list[int] = []
    stack = [1]
    parent[1] = -1
    while stack:
        u = stack.pop()
        order.append(u)
        for v, _w in g[u]:
            if v == parent[u]:
                continue
            parent[v] = u
            stack.append(v)

    sub = [0] * (n + 1)
    down = [0] * (n + 1)
    for u in reversed(order):
        sub[u] = pop[u - 1]
        for v, w in g[u]:
            if v == parent[u]:
                continue
            sub[u] += sub[v]
            down[u] += down[v] + sub[v] * w

    total_pop = sum(pop)
    cost = [0] * (n + 1)
    cost[1] = down[1]
    for u in order:
        for v, w in g[u]:
            if v == parent[u]:
                continue
            cost[v] = cost[u] + (total_pop - 2 * sub[v]) * w

    best = min(cost[1:])
    hubs = [i for i in range(1, n + 1) if cost[i] == best]
    return f"{best}\n{' '.join(map(str, hubs))}\n"


# --- J. Agdao Market Price Board ------------------------------------------------------


class _MaxCountSeg:
    __slots__ = ("n", "mx", "cnt", "lazy")

    def __init__(self, arr: list[int]):
        self.n = len(arr)
        size = 4 * self.n + 4
        self.mx = [0] * size
        self.cnt = [0] * size
        self.lazy = [0] * size
        self._build(1, 0, self.n - 1, arr)

    def _build(self, node: int, l: int, r: int, arr: list[int]) -> None:
        if l == r:
            self.mx[node] = arr[l]
            self.cnt[node] = 1
            return
        mid = (l + r) // 2
        self._build(node * 2, l, mid, arr)
        self._build(node * 2 + 1, mid + 1, r, arr)
        self._pull(node)

    def _pull(self, node: int) -> None:
        left, right = node * 2, node * 2 + 1
        if self.mx[left] > self.mx[right]:
            self.mx[node] = self.mx[left]
            self.cnt[node] = self.cnt[left]
        elif self.mx[right] > self.mx[left]:
            self.mx[node] = self.mx[right]
            self.cnt[node] = self.cnt[right]
        else:
            self.mx[node] = self.mx[left]
            self.cnt[node] = self.cnt[left] + self.cnt[right]

    def _apply(self, node: int, val: int) -> None:
        self.mx[node] += val
        self.lazy[node] += val

    def _push(self, node: int) -> None:
        if self.lazy[node]:
            self._apply(node * 2, self.lazy[node])
            self._apply(node * 2 + 1, self.lazy[node])
            self.lazy[node] = 0

    def add(self, ql: int, qr: int, val: int, node: int = 1, l: int = 0, r: int | None = None) -> None:
        if r is None:
            r = self.n - 1
        if qr < l or r < ql:
            return
        if ql <= l and r <= qr:
            self._apply(node, val)
            return
        self._push(node)
        mid = (l + r) // 2
        self.add(ql, qr, val, node * 2, l, mid)
        self.add(ql, qr, val, node * 2 + 1, mid + 1, r)
        self._pull(node)

    def query(self, ql: int, qr: int, node: int = 1, l: int = 0, r: int | None = None) -> tuple[int, int]:
        if r is None:
            r = self.n - 1
        if qr < l or r < ql:
            return (-10**30, 0)
        if ql <= l and r <= qr:
            return (self.mx[node], self.cnt[node])
        self._push(node)
        mid = (l + r) // 2
        lm, lc = self.query(ql, qr, node * 2, l, mid)
        rm, rc = self.query(ql, qr, node * 2 + 1, mid + 1, r)
        if lm > rm:
            return (lm, lc)
        if rm > lm:
            return (rm, rc)
        return (lm, lc + rc)


def solve_market(inp: str) -> str:
    t = _ints(inp)
    n, q = t[0], t[1]
    a = t[2 : 2 + n]
    seg = _MaxCountSeg(a)
    idx = 2 + n
    out = []
    for _ in range(q):
        typ = t[idx]
        idx += 1
        if typ == 1:
            l, r, x = t[idx], t[idx + 1], t[idx + 2]
            idx += 3
            seg.add(l - 1, r - 1, x)
        else:
            l, r = t[idx], t[idx + 1]
            idx += 2
            mx, cnt = seg.query(l - 1, r - 1)
            out.append(f"{mx} {cnt}")
    return "\n".join(out) + "\n"


# --- Spec / statement -----------------------------------------------------------------


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
    solve: Callable[[str], str]
    samples: list[str]
    hidden: list[str] = field(default_factory=list)
    time_limit_ms: int = 1000
    memory_limit_mb: int = 512
    fast_io: bool = False

    def statement(self) -> str:
        constraints = "\n".join(
            f"- {line}" for line in self.constraints_md.strip().splitlines() if line.strip()
        )
        parts = [
            f"# {self.title}\n\n{self.story}\n\n",
            f"### Input\n{self.input_md}\n\n",
            f"### Output\n{self.output_md}\n\n",
            f"### Constraints\n{constraints}\n",
            SOLUTION_NOTE,
        ]
        for i, sample in enumerate(self.samples, 1):
            sample_out = self.solve(sample)
            parts.append(
                f"\n### Sample {i}\n**Input**\n```\n{sample}```\n"
                f"**Output**\n```\n{sample_out}```\n"
            )
        if self.fast_io:
            parts.append(FAST_IO_NOTE)
        return "".join(parts)


def _load_meta() -> list[dict]:
    return json.loads(META_PATH.read_text(encoding="utf-8"))


def _meta_by_letter() -> dict[str, dict]:
    return {row["letter"]: row for row in _load_meta()}


def _samples_from(meta: dict) -> list[str]:
    return [_ensure_nl(s["input"]) for s in meta["samples"]]


def _fmt_input(meta: dict) -> str:
    text = meta["input_format"].strip()
    # Keep as paragraphs; soft-break lines already joined in JSON.
    return text


def _fmt_output(meta: dict) -> str:
    return meta["output_format"].strip()


def _fmt_constraints(meta: dict) -> str:
    return meta["constraints"].replace("\u2264", "≤").replace("\u00d7", "×")


def _fmt_story(meta: dict) -> str:
    return meta["statement"].replace("\u2264", "≤").replace("\u00d7", "×").replace("\u03a3", "Σ")


# --- Hidden-case builders -------------------------------------------------------------


def _durian_case(rng: random.Random, n: int) -> str:
    rows = [f"{rng.randint(1, 10**6)} {rng.randint(1, 10**4)}" for _ in range(n)]
    return "1\n" + f"{n}\n" + "\n".join(rows) + "\n"


def _jeepney_case(ops: list[tuple[str, str]]) -> str:
    return f"{len(ops)}\n" + "".join(f"{op} {x}\n" for op, x in ops)


def _coop_case(a: list[int], k: int) -> str:
    return f"{len(a)} {k}\n{' '.join(map(str, a))}\n"


def _scoreboard_case(teams: list[str], p: int, logs: list[str]) -> str:
    return (
        f"{len(teams)} {p} {len(logs)}\n"
        + "\n".join(teams)
        + "\n"
        + "\n".join(logs)
        + ("\n" if logs else "")
    )


def _ferry_case(cases: list[tuple[int, int, int, list[int]]]) -> str:
    parts = [str(len(cases))]
    for n, k, p, w in cases:
        parts.append(f"{n} {k} {p}")
        parts.append(" ".join(map(str, w)))
    return "\n".join(parts) + "\n"


def _flood_case(grids: list[list[str]]) -> str:
    parts = [str(len(grids))]
    for g in grids:
        parts.append(f"{len(g)} {len(g[0])}")
        parts.extend(g)
    return "\n".join(parts) + "\n"


def _toll_case(n: int, edges: list[tuple[int, int, int]], k: int) -> str:
    return f"{n} {len(edges)} {k}\n" + "".join(f"{u} {v} {w}\n" for u, v, w in edges)


def _smx_case(g: int, jobs: list[tuple[int, int, int]]) -> str:
    return f"{len(jobs)} {g}\n" + "".join(f"{s} {e} {p}\n" for s, e, p in jobs)


def _health_case(pop: list[int], edges: list[tuple[int, int, int]]) -> str:
    n = len(pop)
    return f"{n}\n{' '.join(map(str, pop))}\n" + "".join(f"{u} {v} {w}\n" for u, v, w in edges)


def _market_case(a: list[int], ops: list[list[int]]) -> str:
    lines = [f"{len(a)} {len(ops)}", " ".join(map(str, a))]
    for op in ops:
        lines.append(" ".join(map(str, op)))
    return "\n".join(lines) + "\n"


def build_specs() -> list[Spec]:
    meta = _meta_by_letter()
    specs: list[Spec] = []

    # A
    m = meta["A"]
    rng = random.Random(3001)
    specs.append(Spec(
        slug="durian-stall-ledger",
        title=m["title"],
        difficulty=Problem.Difficulty.EASY,
        tags=f"{TAG},arrays,overflow",
        story=_fmt_story(m),
        input_md=_fmt_input(m),
        output_md=_fmt_output(m),
        constraints_md=_fmt_constraints(m),
        solve=solve_durian,
        time_limit_ms=1000,
        memory_limit_mb=512,
        samples=_samples_from(m),
        hidden=[
            "1\n1\n1 1\n",
            "1\n3\n1 1\n1 1\n1 1\n",
            _durian_case(rng, 20),
            _durian_case(rng, 200),
            "2\n2\n1000000000 10000\n1 1\n1\n5\n2 3\n4 5\n6 7\n8 9\n1 10000\n",
        ],
    ))

    # B
    m = meta["B"]
    rng = random.Random(3002)
    long_s = "".join(chr(ord("A") + rng.randrange(3)) for _ in range(200))
    specs.append(Spec(
        slug="jeepney-signboard-codes",
        title=m["title"],
        difficulty=Problem.Difficulty.EASY,
        tags=f"{TAG},strings,run-length",
        story=_fmt_story(m),
        input_md=_fmt_input(m),
        output_md=_fmt_output(m),
        constraints_md=_fmt_constraints(m),
        solve=solve_jeepney,
        time_limit_ms=1000,
        memory_limit_mb=512,
        samples=_samples_from(m),
        hidden=[
            _jeepney_case([("E", "A"), ("D", "B2")]),
            _jeepney_case([("E", "ABCDEFG")]),
            _jeepney_case([("E", "AAAAA"), ("D", "A5"), ("E", long_s)]),
            _jeepney_case([("D", _encode_runs("ZZZZZZZZZZ" * 5))]),
        ],
    ))

    # C — sum == K (not modulo)
    m = meta["C"]
    rng = random.Random(3003)
    specs.append(Spec(
        slug="cooperative-ledger-periods",
        title=m["title"],
        difficulty=Problem.Difficulty.MEDIUM,
        tags=f"{TAG},prefix-sum,hashmap",
        story=_fmt_story(m),
        input_md=_fmt_input(m),
        output_md=_fmt_output(m),
        constraints_md=_fmt_constraints(m),
        solve=solve_cooperative,
        time_limit_ms=1000,
        memory_limit_mb=512,
        fast_io=True,
        samples=_samples_from(m),
        hidden=[
            _coop_case([5], 5),
            _coop_case([1, -1, 1, -1], 0),
            _coop_case([rng.randint(-50, 50) for _ in range(40)], 3),
            _coop_case([rng.randint(-1000, 1000) for _ in range(500)], rng.randint(-100, 100)),
        ],
    ))

    # D
    m = meta["D"]
    specs.append(Spec(
        slug="kadayawan-cup-scoreboard",
        title=m["title"],
        difficulty=Problem.Difficulty.MEDIUM,
        tags=f"{TAG},simulation,sorting",
        story=_fmt_story(m),
        input_md=_fmt_input(m),
        output_md=_fmt_output(m),
        constraints_md=_fmt_constraints(m),
        solve=solve_scoreboard,
        time_limit_ms=1000,
        memory_limit_mb=512,
        samples=_samples_from(m),
        hidden=[
            _scoreboard_case(["solo"], 1, []),
            _scoreboard_case(
                ["t1", "t2"],
                2,
                ["0 t1 A WA", "1 t1 A AC", "2 t2 A AC", "3 t2 B AC"],
            ),
            _scoreboard_case(
                ["zeta", "alpha", "beta"],
                1,
                ["10 zeta A CE", "10 zeta A WA", "20 zeta A AC", "20 alpha A AC"],
            ),
            _scoreboard_case(
                [f"team{i}" for i in range(5)],
                3,
                [
                    "1 team0 A AC",
                    "2 team1 A WA",
                    "3 team1 A AC",
                    "4 team2 B AC",
                    "5 team3 C TLE",
                    "6 team3 C AC",
                    "7 team4 A RTE",
                ],
            ),
        ],
    ))

    # E
    m = meta["E"]
    rng = random.Random(3005)
    specs.append(Spec(
        slug="samal-ferry",
        title=m["title"],
        difficulty=Problem.Difficulty.MEDIUM,
        tags=f"{TAG},binary-search,greedy",
        story=_fmt_story(m),
        input_md=_fmt_input(m),
        output_md=_fmt_output(m),
        constraints_md=_fmt_constraints(m),
        solve=solve_ferry,
        time_limit_ms=1000,
        memory_limit_mb=512,
        samples=_samples_from(m),
        hidden=[
            _ferry_case([(1, 1, 1, [7])]),
            _ferry_case([(3, 1, 3, [1, 1, 1])]),
            _ferry_case([(5, 2, 3, [3, 3, 3, 3, 3])]),
            _ferry_case([
                (10, 5, 2, [rng.randint(1, 100) for _ in range(10)]),
                (8, 3, 4, [rng.randint(1, 50) for _ in range(8)]),
            ]),
        ],
    ))

    # F
    m = meta["F"]
    specs.append(Spec(
        slug="flash-flood-matina",
        title=m["title"],
        difficulty=Problem.Difficulty.HARD,
        tags=f"{TAG},bfs,grid",
        story=_fmt_story(m),
        input_md=_fmt_input(m),
        output_md=_fmt_output(m),
        constraints_md=_fmt_constraints(m),
        solve=solve_flood,
        time_limit_ms=2000,
        memory_limit_mb=512,
        samples=_samples_from(m),
        hidden=[
            _flood_case([["SE"]]),
            _flood_case([["S.E"], ["###"], ["W.."]]),
            _flood_case([["S...E"], [".###."], ["W...."]]),
            _flood_case([
                [".....", ".#S#.", ".#.#.", "W...E"],
                ["E.S.W"],
            ]),
        ],
    ))

    # G
    m = meta["G"]
    rng = random.Random(3007)
    chain = [(i, i + 1, rng.randint(1, 100)) for i in range(1, 20)]
    specs.append(Spec(
        slug="davao-river-toll-passes",
        title=m["title"],
        difficulty=Problem.Difficulty.HARD,
        tags=f"{TAG},dijkstra,shortest-path",
        story=_fmt_story(m),
        input_md=_fmt_input(m),
        output_md=_fmt_output(m),
        constraints_md=_fmt_constraints(m),
        solve=solve_toll,
        time_limit_ms=2000,
        memory_limit_mb=512,
        fast_io=True,
        samples=_samples_from(m),
        hidden=[
            _toll_case(2, [(1, 2, 5)], 0),
            _toll_case(2, [(1, 2, 5)], 1),
            _toll_case(4, [(1, 2, 1), (2, 3, 1), (3, 4, 1), (1, 4, 100)], 1),
            _toll_case(20, chain, 2),
        ],
    ))

    # H
    m = meta["H"]
    rng = random.Random(3008)
    jobs_mid = []
    for i in range(30):
        s = rng.randint(0, 200)
        e = s + rng.randint(1, 20)
        jobs_mid.append((s, e, rng.randint(1, 1000)))
    specs.append(Spec(
        slug="smx-hall-bookings",
        title=m["title"],
        difficulty=Problem.Difficulty.HARD,
        tags=f"{TAG},dp,interval-scheduling",
        story=_fmt_story(m),
        input_md=_fmt_input(m),
        output_md=_fmt_output(m),
        constraints_md=_fmt_constraints(m),
        solve=solve_smx,
        time_limit_ms=2000,
        memory_limit_mb=512,
        fast_io=True,
        samples=_samples_from(m),
        hidden=[
            _smx_case(0, [(0, 1, 10)]),
            _smx_case(5, [(0, 10, 1), (10, 20, 1), (15, 25, 100)]),
            _smx_case(1, jobs_mid),
            _smx_case(0, [(i, i + 1, 1) for i in range(50)]),
        ],
    ))

    # I
    m = meta["I"]
    rng = random.Random(3009)
    # path of 15 nodes
    path_pop = [rng.randint(1, 10) for _ in range(15)]
    path_edges = [(i, i + 1, rng.randint(1, 5)) for i in range(1, 15)]
    # star
    star_pop = [1] * 10
    star_edges = [(1, i, 1) for i in range(2, 11)]
    specs.append(Spec(
        slug="barangay-health-hub",
        title=m["title"],
        difficulty=Problem.Difficulty.HARD,
        tags=f"{TAG},tree-dp,rerooting",
        story=_fmt_story(m),
        input_md=_fmt_input(m),
        output_md=_fmt_output(m),
        constraints_md=_fmt_constraints(m),
        solve=solve_health,
        time_limit_ms=2000,
        memory_limit_mb=512,
        fast_io=True,
        samples=_samples_from(m),
        hidden=[
            _health_case([9], []),
            _health_case([1, 100], [(1, 2, 1)]),
            _health_case(path_pop, path_edges),
            _health_case(star_pop, star_edges),
        ],
    ))

    # J
    m = meta["J"]
    rng = random.Random(3010)
    a = [rng.randint(-100, 100) for _ in range(20)]
    ops = []
    for _ in range(30):
        if rng.random() < 0.4:
            l = rng.randint(1, 20)
            r = rng.randint(l, 20)
            ops.append([1, l, r, rng.randint(-50, 50)])
        else:
            l = rng.randint(1, 20)
            r = rng.randint(l, 20)
            ops.append([2, l, r])
    specs.append(Spec(
        slug="agdao-market-price-board",
        title=m["title"],
        difficulty=Problem.Difficulty.HARD,
        tags=f"{TAG},segment-tree,lazy-propagation",
        story=_fmt_story(m),
        input_md=_fmt_input(m),
        output_md=_fmt_output(m),
        constraints_md=_fmt_constraints(m),
        solve=solve_market,
        time_limit_ms=3000,
        memory_limit_mb=1024,
        fast_io=True,
        samples=_samples_from(m),
        hidden=[
            _market_case([42], [[2, 1, 1]]),
            _market_case([1, 2, 3], [[2, 1, 3], [1, 1, 3, 5], [2, 1, 3]]),
            _market_case(a, ops),
            _market_case(
                [0] * 10,
                [[1, 1, 10, 7], [2, 1, 10], [1, 5, 5, -3], [2, 1, 10], [2, 5, 5]],
            ),
        ],
    ))

    return specs


class Command(BaseCommand):
    help = "Create or update the Davao Regional ICPC Java training set (10 problems)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--draft",
            action="store_true",
            help="Leave the problems unpublished (students cannot see them yet).",
        )

    def handle(self, *args, **options):
        owner = (
            User.objects.filter(is_superuser=True).order_by("id").first()
            or User.objects.filter(role=User.Role.ADMIN).order_by("id").first()
        )
        for spec in build_specs():
            cases = [(True, _ensure_nl(inp)) for inp in spec.samples] + [
                (False, _ensure_nl(inp)) for inp in spec.hidden
            ]
            expected = [_ensure_nl(spec.solve(inp)) for _, inp in cases]
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
                        "memory_limit_mb": spec.memory_limit_mb,
                        "created_by": owner,
                    },
                )
                problem.test_cases.all().delete()
                for order, ((is_sample, inp), out) in enumerate(zip(cases, expected), start=1):
                    TestCase.objects.create(
                        problem=problem,
                        order=order,
                        is_sample=is_sample,
                        input_data=inp,
                        expected_output=out,
                    )
            self.stdout.write(self.style.SUCCESS(
                f"{'Created' if created else 'Updated'} {spec.slug} "
                f"({len(spec.samples)} visible + {len(spec.hidden)} hidden tests)"
            ))
