"""Seed the "Number Theory Problem Set in Java" (8 problems).

One problem per technique: fast exponentiation, modular inverse, sieve and
smallest prime factor, divisor functions, extended Euclid, Chinese Remainder
Theorem, binomial coefficients mod p, and Mobius with divisor blocks.

Each problem gets two visible sample tests and several hidden ones. Hidden
tests come from fixed seeds, so every run produces the same data, and the
expected outputs come from the reference solvers below. Each set includes a
maximum-size case that the slow, obvious approach cannot finish in time.

    python manage.py seed_number_theory            # create or update, published
    python manage.py seed_number_theory --draft    # leave unpublished
"""
from __future__ import annotations

import math
import random
from array import array
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Callable

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from problems.models import Problem, TestCase

User = get_user_model()
TAG = "number-theory"
MOD = 1_000_000_007


def _ints(text: str) -> list[int]:
    return [int(x) for x in text.split()]


# --- 1. fast exponentiation -----------------------------------------------------------


def solve_powers(inp: str) -> str:
    t = _ints(inp)
    return "".join(f"{pow(t[1 + 2 * i], t[2 + 2 * i], MOD)}\n" for i in range(t[0]))


# --- 2. modular inverse -----------------------------------------------------------------


def solve_fractions(inp: str) -> str:
    t = _ints(inp)
    total = 0
    for i in range(t[0]):
        p, q = t[1 + 2 * i], t[2 + 2 * i]
        total = (total + p % MOD * pow(q % MOD, MOD - 2, MOD)) % MOD
    return f"{total}\n"


# --- 3. sieve / smallest prime factor ---------------------------------------------------

SIEVE_N = 10_000_000


@lru_cache(maxsize=1)
def _spf() -> array:
    """Smallest prime factor for every x <= SIEVE_N (0 means x is prime).

    Slice assignment from the largest prime down leaves the smallest prime
    factor in each slot, and runs in C, so 10^7 takes about a second."""
    spf = array("i", bytes(4 * (SIEVE_N + 1)))
    limit = math.isqrt(SIEVE_N)
    small = [p for p in range(2, limit + 1) if all(p % d for d in range(2, math.isqrt(p) + 1))]
    for p in reversed(small):
        start = p * p
        count = (SIEVE_N - start) // p + 1
        spf[start::p] = array("i", [p]) * count
    return spf


def _factor_small(x: int) -> list[tuple[int, int]]:
    spf = _spf()
    out = []
    while x > 1:
        p = spf[x] or x
        e = 0
        while x % p == 0:
            x //= p
            e += 1
        out.append((p, e))
    return out


def solve_factor_queries(inp: str) -> str:
    t = _ints(inp)
    lines = []
    for x in t[1 : 1 + t[0]]:
        lines.append("1" if x == 1 else " ".join(f"{p}^{e}" for p, e in _factor_small(x)))
    return "\n".join(lines) + "\n"


# --- 4. divisor functions ----------------------------------------------------------------


def _is_prime(n: int) -> bool:
    if n < 2:
        return False
    for p in (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37):
        if n % p == 0:
            return n == p
    d, s = n - 1, 0
    while d % 2 == 0:
        d //= 2
        s += 1
    for a in (2, 3, 5, 7, 11, 13, 17):  # deterministic far beyond 10^12
        x = pow(a, d, n)
        if x in (1, n - 1):
            continue
        for _ in range(s - 1):
            x = x * x % n
            if x == n - 1:
                break
        else:
            return False
    return True


def _rho(n: int) -> int:
    if n % 2 == 0:
        return 2
    rng = random.Random(n)
    while True:
        c = rng.randrange(1, n)
        x = y = rng.randrange(2, n)
        d = 1
        while d == 1:
            x = (x * x + c) % n
            y = (y * y + c) % n
            y = (y * y + c) % n
            d = math.gcd(abs(x - y), n)
        if d != n:
            return d


def _factor(n: int) -> dict[int, int]:
    out: dict[int, int] = {}
    stack = [n] if n > 1 else []
    while stack:
        m = stack.pop()
        if m == 1:
            continue
        if _is_prime(m):
            out[m] = out.get(m, 0) + 1
            continue
        d = _rho(m)
        stack += [d, m // d]
    return out


def solve_divisor_report(inp: str) -> str:
    t = _ints(inp)
    lines = []
    for n in t[1 : 1 + t[0]]:
        d, sigma, phi = 1, 1, n
        for p, e in _factor(n).items():
            d *= e + 1
            sigma *= (p ** (e + 1) - 1) // (p - 1)
            phi = phi // p * (p - 1)
        lines.append(f"{d} {sigma} {phi}")
    return "\n".join(lines) + "\n"


# --- 5. extended Euclid -----------------------------------------------------------------


def _extgcd(a: int, b: int) -> tuple[int, int, int]:
    if b == 0:
        return a, 1, 0
    g, x, y = _extgcd(b, a % b)
    return g, y, x - a // b * y


def solve_scale(inp: str) -> str:
    t = _ints(inp)
    lines = []
    for i in range(t[0]):
        a, b, c = t[1 + 3 * i : 4 + 3 * i]
        g, x0, _ = _extgcd(a, b)
        if c % g:
            lines.append("-1")
            continue
        step = b // g
        x = x0 * (c // g) % step
        lines.append(f"{x} {(c - a * x) // b}")
    return "\n".join(lines) + "\n"


# --- 6. Chinese Remainder Theorem -------------------------------------------------------


def solve_crt(inp: str) -> str:
    t = _ints(inp)
    big_a, big_m = 0, 1
    for i in range(t[0]):
        a, m = t[1 + 2 * i], t[2 + 2 * i]
        g = math.gcd(big_m, m)
        if (a - big_a) % g:
            return "-1\n"
        mg = m // g
        k = (a - big_a) // g % mg * pow(big_m // g % mg, -1, mg) % mg if mg > 1 else 0
        big_a += big_m * k
        big_m = big_m // g * m
        big_a %= big_m
    return f"{big_a}\n"


# --- 7. binomial coefficients mod p -----------------------------------------------------


@lru_cache(maxsize=1)
def _factorials(limit: int = 2_000_000) -> tuple[list[int], list[int]]:
    fact = [1] * (limit + 1)
    for i in range(1, limit + 1):
        fact[i] = fact[i - 1] * i % MOD
    inv = [1] * (limit + 1)
    inv[limit] = pow(fact[limit], MOD - 2, MOD)
    for i in range(limit, 0, -1):
        inv[i - 1] = inv[i] * i % MOD
    return fact, inv


def solve_grid(inp: str) -> str:
    t = _ints(inp)
    fact, inv = _factorials()
    lines = []
    for i in range(t[0]):
        n, m = t[1 + 2 * i], t[2 + 2 * i]
        lines.append(str(fact[n + m] * inv[n] % MOD * inv[m] % MOD))
    return "\n".join(lines) + "\n"


# --- 8. Mobius / divisor blocks ------------------------------------------------------
# Coprime ordered pairs in [1, n]^2 = 2 * (phi(1) + ... + phi(n)) - 1. The
# totient sum is computed with a table for small n and the memoised identity
# S(n) = n(n+1)/2 - sum_{d=2..n} S(n // d) above it.

_PHI_TABLE_N = 200_000


@lru_cache(maxsize=1)
def _phi_prefix() -> list[int]:
    phi = list(range(_PHI_TABLE_N + 1))
    for p in range(2, _PHI_TABLE_N + 1):
        if phi[p] == p:
            for k in range(p, _PHI_TABLE_N + 1, p):
                phi[k] -= phi[k] // p
    prefix = [0] * (_PHI_TABLE_N + 1)
    for i in range(1, _PHI_TABLE_N + 1):
        prefix[i] = prefix[i - 1] + phi[i]
    return prefix


@lru_cache(maxsize=None)
def _phi_sum(n: int) -> int:
    if n <= _PHI_TABLE_N:
        return _phi_prefix()[n]
    total = n * (n + 1) // 2
    d = 2
    while d <= n:
        q = n // d
        last = n // q
        total -= (last - d + 1) * _phi_sum(q)
        d = last + 1
    return total


def solve_coprime(inp: str) -> str:
    t = _ints(inp)
    return "".join(f"{2 * _phi_sum(n) - 1}\n" for n in t[1 : 1 + t[0]])


# --- input builders and generators ------------------------------------------------------


def _pairs_input(pairs) -> str:
    return f"{len(pairs)}\n" + "".join(f"{a} {b}\n" for a, b in pairs)


def _list_input(values) -> str:
    return f"{len(values)}\n" + "".join(f"{v}\n" for v in values)


def _triples_input(rows) -> str:
    return f"{len(rows)}\n" + "".join(f"{a} {b} {c}\n" for a, b, c in rows)


def _prime_below(n: int) -> int:
    while not _is_prime(n):
        n -= 1
    return n


def _crt_case(rng, n: int, consistent: bool) -> str:
    """n congruences whose moduli all divide one L <= 10^18 (so their lcm fits),
    taken from a secret X; an inconsistent case breaks one of them."""
    base = [(2, 10), (3, 6), (5, 4), (7, 3), (11, 2), (13, 2), (17, 1)]  # L ~ 5.6e16
    big_l = 1
    for p, e in base:
        big_l *= p**e
    secret = rng.randrange(big_l)
    rows = []
    while len(rows) < n:
        m = 1
        for p, e in base:
            m *= p ** rng.randint(0, e)
        if 2 <= m <= 1_000_000_000:
            rows.append((secret % m, m))
    if not consistent:
        # Flip the parity of one even modulus's residue: it then contradicts
        # every other even modulus, so no x exists.
        evens = [i for i, (_, m) in enumerate(rows) if m % 2 == 0]
        i = evens[len(evens) // 2]
        a, m = rows[i]
        rows[i] = ((a + 1) % m, m)
    return _pairs_input(rows)


@dataclass
class Spec:
    slug: str
    title: str
    difficulty: str
    technique_tag: str
    idea: str
    task: str
    input_md: str
    output_md: str
    solve: Callable[[str], str]
    samples: list[str]
    hidden: list[str] = field(default_factory=list)
    time_limit_ms: int = 2000
    memory_limit_mb: int = 256

    def statement(self) -> str:
        parts = [
            f"# {self.title}\n\n### The idea\n{self.idea}\n\n### Task\n{self.task}\n\n"
            f"### Input\n{self.input_md}\n\n### Output\n{self.output_md}\n"
        ]
        for i, sample in enumerate(self.samples, 1):
            parts.append(
                f"\n### Sample {i}\n**Input**\n```\n{sample}```\n**Output**\n```\n{self.solve(sample)}```\n"
            )
        parts.append(
            "\n### Fast input and output\n"
            "Inputs can have hundreds of thousands of lines. Read with `BufferedReader` + "
            "`StringTokenizer` and print once from a `StringBuilder`; `Scanner` and one "
            "`println` per answer are too slow.\n"
        )
        return "".join(parts)


def build_specs() -> list[Spec]:
    specs = []

    # 1. Big Powers
    rng = random.Random(2001)
    e18 = 10**18
    specs.append(Spec(
        slug="big-powers", title="Big Powers", difficulty=Problem.Difficulty.EASY,
        technique_tag="fast-exponentiation",
        idea=(
            "Computing a^b by multiplying b times is far too slow when b is 10^18. Fast exponentiation "
            "squares the base and halves the exponent, so it needs only about 60 steps. Reducing mod m "
            "after every multiply keeps every value inside a `long`."
        ),
        task="For each test case, print a^b mod 1,000,000,007. Treat 0^0 as 1.",
        input_md="The first line holds T (`1 ≤ T ≤ 2·10^5`). Each of the next T lines holds a and b (`0 ≤ a, b ≤ 10^18`).",
        output_md="One answer per line.",
        solve=solve_powers,
        time_limit_ms=4000,
        samples=[_pairs_input([(2, 10), (3, 0), (2, 1000000006)]), _pairs_input([(0, 0), (5, 3)])],
        hidden=[
            _pairs_input([(0, 5), (1, e18), (MOD, 2), (MOD - 1, e18), (e18, e18), (e18, 1)]),
            _pairs_input([(rng.randint(0, 10**9), rng.randint(0, 10**9)) for _ in range(500)]),
            _pairs_input([(rng.randint(0, e18), rng.randint(0, e18)) for _ in range(200_000)]),
            _pairs_input([(rng.randint(0, 10), rng.randint(e18 - 10**6, e18)) for _ in range(200_000)]),
        ],
    ))

    # 2. Fractions Mod Prime
    rng = random.Random(2002)
    specs.append(Spec(
        slug="fractions-mod-prime", title="Fractions Mod Prime", difficulty=Problem.Difficulty.MEDIUM,
        technique_tag="modular-inverse",
        idea=(
            "You cannot divide under a modulus directly. Instead, multiply by the modular inverse: the "
            "number q⁻¹ with q · q⁻¹ ≡ 1 (mod p). When p is prime, Fermat's little theorem gives "
            "q⁻¹ = q^(p−2) mod p, which is one call to the power function from Big Powers."
        ),
        task="Given n fractions pᵢ / qᵢ, their sum is a fraction P / Q. Print P · Q⁻¹ mod 1,000,000,007.",
        input_md=(
            "The first line holds n (`1 ≤ n ≤ 2·10^5`). Each of the next n lines holds pᵢ and qᵢ "
            "(`0 ≤ pᵢ ≤ 10^9`, `1 ≤ qᵢ ≤ 10^9`, and no qᵢ is a multiple of 1,000,000,007)."
        ),
        output_md="One integer.",
        solve=solve_fractions,
        time_limit_ms=3000,
        samples=[_pairs_input([(1, 2), (1, 3)]), _pairs_input([(1, 2), (1, 2), (0, 5)])],
        hidden=[
            _pairs_input([(3, 1)]),
            _pairs_input([(0, 7)]),
            _pairs_input([(rng.randint(0, 100), rng.randint(1, 100)) for _ in range(1000)]),
            _pairs_input([(rng.randint(0, 10**9), rng.randint(1, 10**9)) for _ in range(200_000)]),
            _pairs_input([(10**9, 999_999_999)] * 200_000),
        ],
    ))

    # 3. Factor Queries
    rng = random.Random(2003)
    spf = _spf()
    big_primes = [x for x in range(SIEVE_N - 400_000, SIEVE_N + 1) if spf[x] == 0][:5000]
    specs.append(Spec(
        slug="factor-queries", title="Factor Queries", difficulty=Problem.Difficulty.MEDIUM,
        technique_tag="sieve",
        idea=(
            "Trial division costs O(√x) per number, which is too slow for 2·10^5 queries. A sieve does "
            "the work once: it records spf[x], the smallest prime factor of every x up to N. After that, "
            "factoring x is just dividing by spf[x] until x reaches 1, which takes O(log x) steps."
        ),
        task=(
            "For each query x, print its prime factorization as `p^e` terms in increasing order of p, "
            "separated by spaces. For x = 1, print `1`."
        ),
        input_md="The first line holds Q (`1 ≤ Q ≤ 2·10^5`). Each of the next Q lines holds one x (`1 ≤ x ≤ 10^7`).",
        output_md="One factorization per line.",
        solve=solve_factor_queries,
        # Sieve 1.2-2.3 s measured, trial division 3.3-3.6 s: correct solutions get headroom.
        time_limit_ms=3000,
        samples=[_list_input([12, 97, 1]), _list_input([2, 360, 9_999_991, 10_000_000])],
        hidden=[
            _list_input([1]),
            _list_input([2**23, 3**14, 2 * 3 * 5 * 7 * 11 * 13 * 17, 9_699_690, 9_999_999]),
            _list_input([rng.randint(1, 1000) for _ in range(1000)]),
            _list_input([rng.randint(1, SIEVE_N) for _ in range(200_000)]),
            _list_input([rng.choice(big_primes) for _ in range(200_000)]),
        ],
    ))

    # 4. Divisor Report
    rng = random.Random(2004)
    near_primes = [_prime_below(rng.randint(10**12 - 10**8, 10**12)) for _ in range(50)]
    mid_primes = [_prime_below(rng.randint(900_000, 1_000_000)) for _ in range(100)]
    specs.append(Spec(
        slug="divisor-report", title="Divisor Report", difficulty=Problem.Difficulty.MEDIUM,
        technique_tag="divisor-functions",
        idea=(
            "Once n is factored as n = ∏ pᵢ^eᵢ, three classic functions follow from simple product formulas:\n\n"
            "- d(n), the number of divisors, is ∏ (eᵢ + 1).\n"
            "- σ(n), the sum of divisors, is ∏ (1 + pᵢ + pᵢ² + … + pᵢ^eᵢ).\n"
            "- φ(n), Euler's totient (how many of 1..n are coprime to n), is n · ∏ (1 − 1/pᵢ).\n\n"
            "For a single n up to 10^12, trial division up to √n = 10^6 is fast enough to factor it."
        ),
        task="For each n, print d(n), σ(n) and φ(n).",
        input_md="The first line holds T (`1 ≤ T ≤ 50`). Each of the next T lines holds n (`1 ≤ n ≤ 10^12`).",
        output_md="Three integers per line, separated by spaces.",
        solve=solve_divisor_report,
        samples=[_list_input([12, 1, 97]), _list_input([2, 1_000_000_000_000, 999_999_999_989])],
        hidden=[
            _list_input([1, 2, 4, 6, 1024]),
            _list_input([rng.randint(1, 10**12) for _ in range(50)]),
            _list_input(near_primes),
            _list_input([mid_primes[2 * i] * mid_primes[2 * i + 1] for i in range(50)]),
            _list_input([963_761_198_400, 735_134_400, 2**39, 3**25, 999_999_999_999] + [rng.randint(1, 10**12) for _ in range(45)]),
        ],
    ))

    # 5. Balance the Scale
    rng = random.Random(2005)

    def scale_row(r, a_max):
        g = min(r.choice([1, 1, 2, 3, 6, r.randint(1, 1000)]), a_max)
        a, b = r.randint(1, a_max // g) * g, r.randint(1, a_max // g) * g
        c = r.randint(-10**9, 10**9)
        if r.random() < 0.7:
            c -= c % math.gcd(a, b)  # usually solvable
        return a, b, c

    specs.append(Spec(
        slug="balance-the-scale", title="Balance the Scale", difficulty=Problem.Difficulty.HARD,
        technique_tag="extended-euclid",
        idea=(
            "The extended Euclidean algorithm finds g = gcd(a, b) together with integers x and y such that "
            "ax + by = g. That solves the linear Diophantine equation ax + by = c: a solution exists exactly "
            "when g divides c, and then (x, y) scaled by c/g is one solution. Every other solution is "
            "x + k·(b/g), y − k·(a/g) for any integer k."
        ),
        task=(
            "You have weights of a grams and b grams, and may put any number on either pan (negative counts "
            "mean the other pan). Find integers x and y with ax + by = c, choosing the solution with the "
            "smallest non-negative x. Print `-1` if none exists."
        ),
        input_md=(
            "The first line holds T (`1 ≤ T ≤ 10^5`). Each of the next T lines holds a, b and c "
            "(`1 ≤ a, b ≤ 10^9`, `|c| ≤ 10^9`)."
        ),
        output_md="x and y separated by a space, or `-1`, one line per test.",
        solve=solve_scale,
        time_limit_ms=3000,
        samples=[_triples_input([(6, 10, 8), (6, 10, 7), (3, 5, 0)]), _triples_input([(1, 1, -5), (10**9, 999_999_999, 1)])],
        hidden=[
            _triples_input([(1, 1, 0), (7, 7, 14), (7, 7, 15), (10**9, 10**9, -10**9), (4, 6, -2)]),
            _triples_input([scale_row(rng, 100) for _ in range(1000)]),
            _triples_input([scale_row(rng, 10**9) for _ in range(100_000)]),
            _triples_input([(rng.randint(1, 10**9), rng.randint(1, 10**9), rng.randint(-10**9, 10**9)) for _ in range(100_000)]),
        ],
    ))

    # 6. Secret Number
    rng = random.Random(2006)
    specs.append(Spec(
        slug="secret-number", title="Secret Number", difficulty=Problem.Difficulty.HARD,
        technique_tag="chinese-remainder",
        idea=(
            "The Chinese Remainder Theorem combines congruences x ≡ a₁ (mod m₁), x ≡ a₂ (mod m₂), … into a "
            "single one, x ≡ A (mod M). Merge two at a time: write x = a₁ + m₁t, solve m₁t ≡ a₂ − a₁ (mod m₂) "
            "for t, and the new modulus is lcm(m₁, m₂). The moduli need not be coprime, but then a solution "
            "exists only if gcd(m₁, m₂) divides a₂ − a₁."
        ),
        task="Find the smallest non-negative x satisfying every congruence, or print `-1` if none exists.",
        input_md=(
            "The first line holds n (`1 ≤ n ≤ 10^5`). Each of the next n lines holds aᵢ and mᵢ "
            "(`1 ≤ mᵢ ≤ 10^9`, `0 ≤ aᵢ < mᵢ`). If a solution exists, the lcm of all mᵢ is at most 10^18."
        ),
        output_md="One integer.",
        solve=solve_crt,
        time_limit_ms=3000,
        samples=[_pairs_input([(2, 3), (3, 5), (2, 7)]), _pairs_input([(1, 4), (2, 6)])],
        hidden=[
            _pairs_input([(0, 1)]),
            _pairs_input([(5, 7)]),
            _pairs_input([(3, 10), (3, 10), (8, 15)]),
            _pairs_input([(rng.randrange(p), p) for p in (999_999_937, 999_999_929)]),  # coprime, lcm ~10^18
            _crt_case(rng, 1000, True),
            _crt_case(rng, 100_000, True),
            _crt_case(rng, 100_000, False),
        ],
    ))

    # 7. Grid Paths
    rng = random.Random(2007)
    specs.append(Spec(
        slug="grid-paths", title="Grid Paths", difficulty=Problem.Difficulty.MEDIUM,
        technique_tag="binomial-coefficients",
        idea=(
            "Counting problems often reduce to C(n, k) = n! / (k! (n−k)!). Under a prime modulus, precompute "
            "every factorial up to N and every inverse factorial; after that, each C(n, k) is two "
            "multiplications. The inverse factorials need only one modular power: compute ifact[N] with "
            "Fermat, then walk down using ifact[i−1] = ifact[i] · i."
        ),
        task=(
            "A robot starts at (0, 0) and moves only right or up. For each query, count the paths to (n, m), "
            "modulo 1,000,000,007."
        ),
        input_md="The first line holds Q (`1 ≤ Q ≤ 2·10^5`). Each of the next Q lines holds n and m (`0 ≤ n, m ≤ 10^6`).",
        output_md="One answer per line.",
        solve=solve_grid,
        time_limit_ms=3000,
        samples=[_pairs_input([(2, 2), (3, 1), (0, 5)]), _pairs_input([(10**6, 10**6), (0, 0)])],
        hidden=[
            _pairs_input([(0, 0), (1, 0), (0, 10**6), (10**6, 1), (500_000, 500_000)]),
            _pairs_input([(rng.randint(0, 20), rng.randint(0, 20)) for _ in range(1000)]),
            _pairs_input([(rng.randint(0, 10**6), rng.randint(0, 10**6)) for _ in range(200_000)]),
            _pairs_input([(rng.randint(900_000, 10**6), rng.randint(900_000, 10**6)) for _ in range(200_000)]),
        ],
    ))

    # 8. Coprime Pairs
    rng = random.Random(2008)
    big_values = [rng.randint(5_000_000, 10_000_000) for _ in range(40)] + [10_000_000]
    specs.append(Spec(
        slug="coprime-pairs", title="Coprime Pairs", difficulty=Problem.Difficulty.HARD,
        technique_tag="mobius",
        idea=(
            "The Möbius function μ(d) is 1 for d = 1, (−1)^k when d is a product of k distinct primes, and 0 "
            "when d has a squared prime factor. Its key property is that summing μ(d) over the common divisors "
            "d of i and j gives 1 if gcd(i, j) = 1 and 0 otherwise. Swapping the order of summation turns "
            "\"count coprime pairs\" into a formula:\n\n"
            "`#{(i, j) : 1 ≤ i, j ≤ n, gcd(i, j) = 1} = Σ_{d=1..n} μ(d) · ⌊n/d⌋²`\n\n"
            "The value ⌊n/d⌋ takes only about 2√n distinct values, so grouping the d's that share it (divisor "
            "blocks) answers each query in O(√n), given prefix sums of μ."
        ),
        task="For each n, count the ordered pairs (i, j) with `1 ≤ i, j ≤ n` and gcd(i, j) = 1.",
        input_md="The first line holds T (`1 ≤ T ≤ 10^4`). Each of the next T lines holds n (`1 ≤ n ≤ 10^7`).",
        output_md="One answer per line.",
        solve=solve_coprime,
        time_limit_ms=3000,
        samples=[_list_input([1, 2, 5, 10]), _list_input([3, 100, 10_000_000])],
        hidden=[
            _list_input([1]),
            _list_input([rng.randint(1, 1000) for _ in range(100)]),
            _list_input([rng.randint(1, 200_000) for _ in range(10_000)]),
            _list_input([rng.choice(big_values) for _ in range(10_000)]),
        ],
    ))

    return specs


class Command(BaseCommand):
    help = "Create or update the Number Theory problem set (8 problems, 2 visible samples each)."

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
            cases = [(True, inp) for inp in spec.samples] + [(False, inp) for inp in spec.hidden]
            expected = [spec.solve(inp) for _, inp in cases]
            with transaction.atomic():
                problem, created = Problem.objects.update_or_create(
                    slug=spec.slug,
                    defaults={
                        "title": spec.title,
                        "statement": spec.statement(),
                        "difficulty": spec.difficulty,
                        "tags": f"{TAG},{spec.technique_tag}",
                        "is_published": not options["draft"],
                        "time_limit_ms": spec.time_limit_ms,
                        "memory_limit_mb": spec.memory_limit_mb,
                        "created_by": owner,
                    },
                )
                problem.test_cases.all().delete()
                for order, ((is_sample, inp), out) in enumerate(zip(cases, expected), start=1):
                    TestCase.objects.create(
                        problem=problem, order=order, is_sample=is_sample,
                        input_data=inp, expected_output=out,
                    )
            self.stdout.write(self.style.SUCCESS(
                f"{'Created' if created else 'Updated'} {spec.slug} "
                f"({len(spec.samples)} visible + {len(spec.hidden)} hidden tests)"
            ))
