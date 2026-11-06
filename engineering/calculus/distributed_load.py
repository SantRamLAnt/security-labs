#!/usr/bin/env python3
"""A lateral with its load spread along it: a Riemann sum (MIT 18.01, Session 46).

Distribution engineering has a standard rule of thumb: if a lateral's load is spread evenly along its
length instead of sitting at the far end, the voltage drop is about half and the losses are
about a third. Both numbers are integrals.

Take a lateral of length L with impedance r per unit length, carrying total load I. Split the
load into N equal pieces at the end of N equal sections. Section k (counting from the source)
carries the load of every piece past it, I * (N - k + 1) / N. Then, relative to putting all of
I at the far end:

    voltage drop ratio  = (1/N) * sum_{k=1..N} (N - k + 1)/N      = (N + 1) / (2N)
    losses ratio        = (1/N) * sum_{k=1..N} ((N - k + 1)/N)^2  = (N + 1)(2N + 1) / (6 N^2)

Those are Riemann sums of f(x) = 1 - x and f(x) = (1 - x)^2 on [0, 1]. As N grows they approach

    integral of (1 - x)   dx from 0 to 1 = 1/2
    integral of (1 - x)^2 dx from 0 to 1 = 1/3

The script computes the sums three ways (term by term, closed form, and by solving Kirchhoff's
current law as a matrix the way Lab J does) and shows the error shrinking like 1/N.

Usage: distributed_load.py [--check]
"""
import sys
from fractions import Fraction

import numpy as np


def by_terms(n):
    drop = sum(Fraction(n - k + 1, n) for k in range(1, n + 1)) / n
    loss = sum(Fraction(n - k + 1, n) ** 2 for k in range(1, n + 1)) / n
    return drop, loss


def closed_form(n):
    return Fraction(n + 1, 2 * n), Fraction((n + 1) * (2 * n + 1), 6 * n * n)


def by_matrix(n):
    """Kirchhoff's current law on a chain of n sections, as in Lab J: M i = d, then drop = sum(z*i)."""
    M = np.eye(n) - np.eye(n, k=1)      # node k: current in from section k, out through section k+1
    d = np.full(n, 1.0 / n)             # each node draws 1/n of the total load
    i = np.linalg.solve(M, d)           # section currents
    z = np.full(n, 1.0 / n)             # each section is 1/n of the total impedance
    return float(np.sum(z * i)), float(np.sum(z * i * i))


def main():
    print("  Spread load vs all of it at the far end (ratios; lumped = 1)")
    print("     N    drop ratio   error vs 1/2   loss ratio   error vs 1/3   matrix check")
    rows = {}
    for n in (1, 2, 5, 10, 100, 1000):
        d, l = by_terms(n)
        assert (d, l) == closed_form(n)
        md, ml = by_matrix(n)
        ok = abs(md - float(d)) < 1e-12 and abs(ml - float(l)) < 1e-12
        rows[n] = (d, l, ok)
        print(f"  {n:5d}    {float(d):.6f}     {float(d) - 0.5:+.6f}      {float(l):.6f}     "
              f"{float(l) - 1/3:+.6f}      {'agrees' if ok else 'DISAGREES'}")
    print("\n  The drop error is exactly 1/(2N), so ten times the sections cuts it by ten.")

    # A worked example in real units. Synthetic numbers, not from any utility.
    I, R, V = 60.0, 0.9, 7967.0          # amps, ohms for the whole lateral, volts line to neutral
    lumped = I * R
    print(f"\n  Example: 60 A on a lateral with 0.9 ohm of resistance, 7,967 V line to neutral")
    print(f"    all load at the end:  drop {lumped:.1f} V ({100 * lumped / V:.2f}%), losses {I * I * R / 1000:.2f} kW")
    print(f"    spread evenly:        drop {lumped / 2:.1f} V ({100 * lumped / 2 / V:.2f}%), losses {I * I * R / 3000:.2f} kW")

    if "--check" in sys.argv:
        bad = []
        if rows[1][:2] != (1, 1): bad.append("N=1 should equal the lumped case")
        if any(not r[2] for r in rows.values()): bad.append("matrix solve disagrees with the sum")
        for n, (d, l, _) in rows.items():
            if d - Fraction(1, 2) != Fraction(1, 2 * n): bad.append(f"drop error at N={n}")
        if abs(float(rows[1000][1]) - 1 / 3) > 6e-4: bad.append("loss ratio not near 1/3")
        print("\n  check:", "PASS" if not bad else f"FAIL {bad}")
        sys.exit(len(bad))


if __name__ == "__main__":
    main()
