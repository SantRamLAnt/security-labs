#!/usr/bin/env python3
"""Measuring the memory hierarchy from Python (MIT 6.004, Chapter 14: Caches and the Memory Hierarchy).

A processor keeps recently used memory in small, fast caches (L1, L2, L3) in front of main
memory. Reading data that's already in a cache is fast. Once the data you're touching is
bigger than a cache, more reads go to the next level down, and each one costs more.

This script measures that two ways with NumPy, so the per-element work runs in compiled code
and Python's own overhead stays small:

  1. Working-set sweep. Gather 4 million values at random positions from an array, for array
     sizes from 16 KiB to 512 MiB. Random positions defeat the hardware prefetcher, so the time
     per read climbs in steps as the array outgrows each cache level.
  2. Stride sweep. Sum every k-th value of a 256 MiB array. Memory moves in 64-byte cache lines
     (8 float64 values), so up to a stride of 8 each step wastes more of every line fetched. The
     simple cache-line model says the time per value should level off after that. On the machines
     I've tried it keeps rising, which points at the prefetcher and memory pages as well. I
     haven't separated those effects.

These are throughput numbers. Independent reads overlap in the processor, so they understate
the latency of a single miss; a pointer-chasing test would measure that directly.

Each point is the median of several runs. The cache sizes reported by lscpu are printed so the
steps can be compared with the hardware. Timings depend on the machine and on whatever else it
is doing; the shape matters more than the exact numbers.

Usage: memory_hierarchy.py [--quick]
"""
import os
import statistics
import subprocess
import sys
import time

import numpy as np

QUICK = "--quick" in sys.argv
READS = 1_000_000 if QUICK else 4_000_000
REPEATS = 3 if QUICK else 5


def cache_sizes():
    try:
        out = subprocess.run(["lscpu"], capture_output=True, text=True).stdout
    except FileNotFoundError:
        return "lscpu not available"
    keep = [l.split(":", 1) for l in out.splitlines()
            if l.split(":")[0].strip() in ("Model name", "L1d cache", "L2 cache", "L3 cache")]
    return "; ".join(f"{k.strip()} {v.strip()}" for k, v in keep)


def time_it(fn, repeats=REPEATS):
    fn()  # warm-up: page in the memory and fill the caches once
    ts = []
    for _ in range(repeats):
        t0 = time.perf_counter()
        fn()
        ts.append(time.perf_counter() - t0)
    return statistics.median(ts)


def working_set(rng):
    print(f"  1. Random reads, {READS:,} per point (ns per read, median of {REPEATS})")
    out = []
    sizes = [16, 64, 256, 1024, 4096, 16384, 65536, 262144] + ([] if QUICK else [524288])
    for kib in sizes:
        n = kib * 1024 // 8
        a = rng.random(n)
        idx = rng.integers(0, n, READS)
        t = time_it(lambda: np.take(a, idx).sum())
        ns = 1e9 * t / READS
        out.append((kib, ns))
        label = f"{kib} KiB" if kib < 1024 else f"{kib // 1024} MiB"
        print(f"     {label:>8s}  {ns:6.2f} ns  " + "#" * min(60, int(ns * 2)))
        del a, idx
    return out


def strides(rng):
    n = (32 if QUICK else 256) * 1024 * 1024 // 8
    a = rng.random(n)
    print(f"\n  2. Sum every k-th value of a {n * 8 // 2**20} MiB array (ns per value read)")
    out = []
    for k in (1, 2, 4, 8, 16, 32, 64):
        view = a[::k]
        t = time_it(lambda: view.sum())
        ns = 1e9 * t / view.size
        out.append((k, ns))
        print(f"     stride {k:3d} ({8 * k:4d} bytes)  {ns:6.2f} ns")
    return out


def main():
    print(f"  Machine: {cache_sizes()}; {os.cpu_count()} logical CPUs; NumPy {np.__version__}\n")
    rng = np.random.default_rng(20261106)
    ws = working_set(rng)
    st = strides(rng)
    small, big = ws[0][1], ws[-1][1]
    print(f"\n  Smallest vs largest working set: {small:.2f} ns vs {big:.2f} ns per read"
          f" ({big / small:.1f}x)")
    print(f"  Stride 1 vs stride 8: {st[0][1]:.2f} vs {st[3][1]:.2f} ns per value"
          f" ({st[3][1] / st[0][1]:.1f}x); stride 8 vs 64: {st[3][1]:.2f} vs {st[6][1]:.2f}")


if __name__ == "__main__":
    main()
