#!/usr/bin/env python3
"""Measure the image redaction check instead of trusting one canary.

Part 1, miss rate. Renders N terminal-style screenshots, each with a fresh random GUID, in the
same layout as the Gate 0 canary. Every image is OCR'd once, then scored twice with the
pattern logic three ways: as first committed in PR #10 (exact group widths, no repair), with
today's tolerant pattern on the raw text, and with today's pattern after repair(). All three
scores come from the same OCR output, so the comparison is paired and only the logic differs.

Zero misses in N images doesn't mean the miss rate is zero. The one-sided 95% upper bound for
zero events in N trials is 1 - 0.05^(1/N), about 3/N. For N = 300 that's just under 1%.

Part 2, threads. Times OCR over the same images with the process pool at one worker per core
and Tesseract's OpenMP thread limit set to 1, 2, 4, or left unset. Unset is what caused the
15-minute Gate 1 run: every worker process starts as many threads as there are cores, so the
machine runs workers x cores threads on cores cores.

GUIDs come from a seeded generator so a run can be repeated exactly. None are real.

Each thread setting runs in its own process with a time limit, so a setting that slows down
badly is recorded as "over the limit" instead of hanging the run.

usage: measure_redaction.py [N] [--threads M] [--repeats R] [--limit SECONDS] [--seed S]
"""
import argparse
import math
import os
import random
import re
import statistics
import subprocess
import sys
import time
import uuid
from concurrent.futures import ProcessPoolExecutor

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(__file__))
import image_scan  # noqa: E402  (sets OMP_THREAD_LIMIT=1 for this process on import)

FONT = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", 15)


def render(guid):
    im = Image.new("RGB", (1100, 90), (12, 12, 12))
    d = ImageDraw.Draw(im)
    d.text((10, 12), "$ az ad sp show --id <canary>", fill=(200, 200, 200), font=FONT)
    d.text((10, 44), f"(AuthorizationFailed) The client '{guid}' does not have authorization",
           fill=(230, 80, 80), font=FONT)
    return im


# The GUID check as first committed (7c29304, PR #10), kept here only to measure it.
V1_H = r"[0-9a-fA-F/lIi|oOsSzZ]"
V1_GUID = rf"(?<![0-9A-Za-z]){V1_H}{{8}}-{V1_H}{{4}}-{V1_H}{{4}}(?:-{V1_H}{{4}}(?:-{V1_H}{{6,12}})?)?"
V1_MAP = str.maketrans({"/": "7", "l": "1", "I": "1", "i": "1", "|": "1", "o": "0", "O": "0",
                        "s": "5", "S": "5", "z": "2", "Z": "2"})


def v1_caught(text):
    for m in re.finditer(V1_GUID, text, re.I):
        v = m.group(0).translate(V1_MAP).lower()
        if re.fullmatch(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}.*", v) and re.search(r"\d", v):
            return True
    return False


def score(guid):
    raw = image_scan.ocr(render(guid))
    v1 = v1_caught(raw)
    before = [v for k, v in image_scan.find(raw) if k == "guid"]
    after = [v for k, v in image_scan.find(image_scan.repair(raw)) if k == "guid"]
    return v1, bool(before), bool(after), guid in after


def set_threads(value):
    if value is None:
        os.environ.pop("OMP_THREAD_LIMIT", None)
    else:
        os.environ["OMP_THREAD_LIMIT"] = str(value)


def ocr_only(guid):
    image_scan.ocr(render(guid))


def upper95(misses, n):
    """One-sided 95% upper bound on the miss rate (exact for zero misses)."""
    if misses == 0:
        return 1 - 0.05 ** (1 / n)
    lo, hi = misses / n, 1.0
    for _ in range(100):  # bisection on P(X <= misses) = 0.05
        mid = (lo + hi) / 2
        cdf = sum(math.comb(n, j) * mid**j * (1 - mid)**(n - j) for j in range(misses + 1))
        lo, hi = (mid, hi) if cdf > 0.05 else (lo, mid)
    return (lo + hi) / 2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("n", type=int, nargs="?", default=300)
    ap.add_argument("--threads", type=int, default=40, help="images for the thread benchmark")
    ap.add_argument("--repeats", type=int, default=3, help="timed runs per thread setting")
    ap.add_argument("--limit", type=int, default=240, help="seconds allowed per timed run")
    ap.add_argument("--seed", type=int, default=20261105)
    ap.add_argument("--bench-one", default=None, help=argparse.SUPPRESS)
    a = ap.parse_args()
    rng = random.Random(a.seed)
    guids = [str(uuid.UUID(int=rng.getrandbits(128), version=4)) for _ in range(a.n)]
    cores = os.cpu_count()
    if a.bench_one is not None:
        value = None if a.bench_one == "unset" else int(a.bench_one)
        with ProcessPoolExecutor(max_workers=cores, initializer=set_threads, initargs=(value,)) as ex:
            t0 = time.time()
            list(ex.map(ocr_only, guids[:a.threads]))
            print(f"{time.time() - t0:.3f}")
        return

    print(f"Redaction check measurement  (seed {a.seed}, {cores} cores, "
          f"tesseract via pytesseract)\n")
    t0 = time.time()
    with ProcessPoolExecutor() as ex:
        res = list(ex.map(score, guids))
    v1, before, after, exact = (sum(r[i] for r in res) for i in range(4))
    n = a.n
    print(f"Part 1: {n} rendered GUIDs, OCR'd once each ({time.time() - t0:.0f} s)")
    for label, c in (("as first committed (PR #10)", v1), ("current pattern, raw text", before),
                     ("current pattern + repair()", after)):
        print(f"  {label:30s} caught {c:4d} / {n}   missed {n - c:3d} ({100 * (n - c) / n:4.1f}%)"
              f"   95% upper bound {100 * upper95(n - c, n):5.2f}%")
    print(f"  read back digit-for-digit after repair(): {exact} / {n} (not required: flagging is the test)")
    print(f"  caught by an earlier version but missed by the current one: "
          f"{sum(1 for r in res if (r[0] or r[1]) and not r[2])}\n")

    if not a.threads:
        return
    m = guids[:a.threads]
    print(f"Part 2: OCR time for {len(m)} images, {cores} worker processes, "
          f"{a.repeats} timed runs per setting")
    base = None
    for value in ("1", "2", "4", "unset"):
        times = []
        for _ in range(a.repeats):
            cmd = [sys.executable, os.path.abspath(__file__), str(a.n), "--threads", str(a.threads),
                   "--seed", str(a.seed), "--bench-one", value]
            try:
                out = subprocess.run(cmd, capture_output=True, text=True, timeout=a.limit,
                                     start_new_session=True)
                times.append(float(out.stdout.strip().splitlines()[-1]))
            except subprocess.TimeoutExpired:
                os.system("pkill -9 tesseract >/dev/null 2>&1")
                times.append(float("inf"))
        finite = [t for t in times if t != float("inf")]
        med = statistics.median(times) if len(finite) * 2 > len(times) else float("inf")
        base = base or med
        runs = ", ".join("over limit" if t == float("inf") else f"{t:.1f}" for t in times)
        shown = f"over {a.limit} s" if med == float("inf") else f"{med:7.1f} s"
        ratio = "" if med == float("inf") else f"({med / base:6.1f}x)"
        print(f"  OMP_THREAD_LIMIT={value:6s} median {shown:>11s} {ratio:9s}  runs: {runs}", flush=True)

if __name__ == "__main__":
    main()
