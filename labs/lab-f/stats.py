#!/usr/bin/env python3
"""LAB F: what ten trials can and can't tell you.

Each configuration in FINDINGS.md was tested with 10 attacks, once each. This script puts a
95% confidence interval around each leak count, using the exact (Clopper-Pearson) binomial
interval, so a result like "0 of 10" is reported with the range of leak rates it's consistent
with instead of as zero.

The binomial maths is written out here (no scipy) so it can be checked line by line:

  P(X <= k) = sum_{j=0..k} C(n, j) p^j (1-p)^(n-j)

  upper bound: the p where P(X <= k) = 0.025
  lower bound: the p where P(X >= k) = 0.025

Both are found by bisection, because P(X <= k) only goes down as p goes up.

One caveat matters more than the maths. The 10 trials per configuration are 10 different
attacks, not the same attack repeated, so they aren't identical trials, and the interval
treats them as if they were. The honest experiment is to repeat each attack many times.

Usage: stats.py [--check]   (--check runs the pinned values and exits non-zero on a mismatch)
"""
import math
import sys

# Leak counts from the FINDINGS.md results table (run 31 Oct 2026, 10 attacks per configuration)
RESULTS = [
    ("naive",              1, 10),
    ("naive + shields",    1, 10),
    ("baseline",           0, 10),
    ("baseline + shields", 0, 10),
    ("guarded",            0, 10),
    ("guarded + shields",  0, 10),
]


def cdf(k, n, p):
    """P(X <= k) for X ~ Binomial(n, p)."""
    return sum(math.comb(n, j) * p**j * (1 - p)**(n - j) for j in range(k + 1))


def bisect(f, lo=0.0, hi=1.0, iters=100):
    """Root of a decreasing function f on [lo, hi]."""
    for _ in range(iters):
        mid = (lo + hi) / 2
        if f(mid) > 0:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def interval(k, n, alpha=0.05):
    upper = 1.0 if k == n else bisect(lambda p: cdf(k, n, p) - alpha / 2)
    # The lower bound for k events is one minus the upper bound for n - k non-events.
    lower = 0.0 if k == 0 else 1 - bisect(lambda q: cdf(n - k, n, q) - alpha / 2)
    return lower, upper


def one_sided_upper(n, alpha=0.05):
    """Zero events in n trials: the largest rate still consistent at 1 - alpha."""
    return 1 - alpha ** (1 / n)


def trials_needed(rate, alpha=0.05):
    """How many clean runs before 'zero leaks' rules out a true rate this high."""
    return math.ceil(math.log(alpha) / math.log(1 - rate))


def main():
    print("  Configuration          leaks   95% interval for the true leak rate")
    print("  ---------------------  ------  -----------------------------------")
    rows = {}
    for name, k, n in RESULTS:
        lo, hi = interval(k, n)
        rows[name] = (lo, hi)
        print(f"  {name:21s}  {k:2d}/{n:<3d}  {100*lo:5.1f}% to {100*hi:5.1f}%")
    print()
    print(f"  Zero leaks in 10 runs still allows a true rate up to {100*one_sided_upper(10):.1f}%"
          " (one-sided, 95%).")
    for r in (0.10, 0.05, 0.01):
        print(f"  To rule out a {100*r:.0f}% leak rate with zero leaks: {trials_needed(r)} clean runs.")

    if "--check" in sys.argv:
        want = {"naive": (0.0025, 0.4450), "baseline": (0.0, 0.3085)}
        bad = [n for n, (lo, hi) in want.items()
               if abs(rows[n][0] - lo) > 5e-4 or abs(rows[n][1] - hi) > 5e-4]
        bad += [] if abs(one_sided_upper(10) - 0.2589) < 5e-4 else ["one-sided 0/10"]
        bad += [] if trials_needed(0.05) == 59 else ["trials for 5%"]
        print("\n  check:", "PASS" if not bad else f"FAIL {bad}")
        sys.exit(len(bad))


if __name__ == "__main__":
    main()
