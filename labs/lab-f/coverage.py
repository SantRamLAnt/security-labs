#!/usr/bin/env python3
"""LAB F: does a "95% interval" actually cover the true rate 95% of the time?

MIT 18.05 (Reading 23a, Confidence Intervals: Three Views) defines 95% confidence as a property
of the procedure: run the experiment many times, build an interval each time, and 95% of those
intervals contain the true value. It also notes that with discrete data, exact 95% may not be
achievable, so a procedure can only promise "at least 95%".

That definition can be checked directly. For a true leak rate p and n = 10 trials:

    coverage(p) = sum over k of  P(X = k | p) * [p is inside the interval built from k]

This script computes that exactly for two procedures, then checks a few points by simulating
the repeated experiments the definition describes:

  - Clopper-Pearson, the exact interval used in stats.py
  - Wald, the textbook normal approximation  p_hat +/- 1.96 * sqrt(p_hat (1 - p_hat) / n)

The Wald interval has a specific failure at 0 of 10: p_hat = 0 gives the interval [0, 0], which
says the rate is exactly zero. That's an empty result reading as a clean one.

Usage: coverage.py [--check]
"""
import math
import random
import sys

from stats import interval  # Clopper-Pearson, written out in stats.py

N = 10
Z = 1.959964


def wald(k, n):
    p = k / n
    half = Z * math.sqrt(p * (1 - p) / n)
    return max(0.0, p - half), min(1.0, p + half)


def pmf(k, n, p):
    return math.comb(n, k) * p**k * (1 - p)**(n - k)


def coverage(method, p, n=N):
    return sum(pmf(k, n, p) for k in range(n + 1)
               if method(k, n)[0] <= p <= method(k, n)[1])


def simulate(method, p, runs, rng, n=N):
    hits = 0
    for _ in range(runs):
        k = sum(rng.random() < p for _ in range(n))
        lo, hi = method(k, n)
        hits += lo <= p <= hi
    return hits / runs


def main():
    cp = {k: interval(k, N) for k in range(N + 1)}            # precompute: 11 possible outcomes
    clopper = lambda k, n: cp[k]                                # noqa: E731
    grid = [i / 1000 for i in range(1, 1000)]
    cp_cov = [coverage(clopper, p) for p in grid]
    wd_cov = [coverage(wald, p) for p in grid]

    print(f"  True coverage of a nominal 95% interval, n = {N} trials (exact)")
    print("  true leak rate   Clopper-Pearson   Wald (normal approx.)")
    for p in (0.01, 0.05, 0.10, 0.20, 0.30, 0.50):
        print(f"      {p:5.2f}            {coverage(clopper, p):6.3f}            {coverage(wald, p):6.3f}")
    print(f"\n  lowest coverage for any rate from 0.001 to 0.999:"
          f"  Clopper-Pearson {min(cp_cov):.3f}   Wald {min(wd_cov):.3f}")
    print(f"  Wald at 0 of 10 gives {wald(0, N)}: zero width, so it never covers a true rate above 0.")

    rng = random.Random(20261106)
    runs = 40000
    print(f"\n  Simulation check ({runs:,} repeated experiments per rate, seed 20261106)")
    sim = {}
    for p in (0.05, 0.20):
        sim[p] = (simulate(clopper, p, runs, rng), simulate(wald, p, runs, rng))
        print(f"      p = {p:.2f}:  Clopper-Pearson {sim[p][0]:.3f} (exact {coverage(clopper, p):.3f})"
              f"   Wald {sim[p][1]:.3f} (exact {coverage(wald, p):.3f})")

    if "--check" in sys.argv:
        bad = []
        if min(cp_cov) < 0.95:
            bad.append("Clopper-Pearson fell below 95%")
        if min(wd_cov) > 0.5:
            bad.append("Wald minimum not below 50%")
        if abs(coverage(wald, 0.05) - 0.401) > 0.002:
            bad.append("Wald coverage at p=0.05")
        for p, (c, w) in sim.items():
            if abs(c - coverage(clopper, p)) > 0.01 or abs(w - coverage(wald, p)) > 0.01:
                bad.append(f"simulation disagrees with exact at p={p}")
        print("\n  check:", "PASS" if not bad else f"FAIL {bad}")
        sys.exit(len(bad))


if __name__ == "__main__":
    main()
