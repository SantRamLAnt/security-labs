#!/usr/bin/env python3
"""Pinned results for topology.py. Exact values, so a change that silently breaks the maths
fails here instead of printing a clean-looking report. Exit code = number of failures."""
import os
import sys

import yaml

sys.path.insert(0, os.path.dirname(__file__))
from topology import analyse  # noqa: E402

HERE = os.path.dirname(__file__)
fails = 0


def check(name, got, want):
    global fails
    ok = got == want
    fails += not ok
    print(f"  {'PASS' if ok else 'FAIL'}  {name:44s} {got!r}" + ("" if ok else f"  (expected {want!r})"))


def run(f):
    return analyse(os.path.join(HERE, f))


def downstream_amps(model, phase):
    """Independent cross-check by walking the tree instead of solving A i = d: the current in
    a section is the device's own load plus every load below it on the same phase."""
    devs = {d["id"]: d for fd in model["feeders"] for d in fd["devices"]
            if phase in d["phases"] and not d.get("ties_to")}
    kids = {k: [d for d in devs if devs[d]["upstream"] == k] for k in devs}

    def total(k):
        return devs[k].get("load_a", 0) + sum(total(c) for c in kids[k])
    return {k: float(total(k)) for k in devs}


normal = run("feeder-normal.yaml")
check("normal: radial on A, B, C", [p["radial"] for p in normal["phases"]], [True] * 3)
amps = {p["phase"]: {s["device"]: s["amps"] for s in p["sections"]} for p in normal["phases"]}
check("normal: CB-101 amps A/B/C (hand: 120+38, 120+22, 120)",
      [amps[x]["CB-101"] for x in "ABC"], [158.0, 142.0, 120.0])
check("normal: R-1021 amps on C (hand: 90+30)", amps["C"]["R-1021"], 120.0)
model = yaml.safe_load(open(os.path.join(HERE, "feeder-normal.yaml")))
check("normal: A i = d matches the tree walk, every section",
      all(abs(amps[x][k] - v) < 0.05 for x in "ABC" for k, v in downstream_amps(model, x).items()),
      True)
check("normal: KCL residual below 1e-9",
      all(p["kcl_residual"] < 1e-9 for p in normal["phases"]), True)
check("normal: largest drop on A, % (hand estimate 1.61)",
      float(max(normal["phases"][0]["voltage_drop_pct"].values())), 1.608)

bad = run("feeder-bad.yaml")
check("bad: loops A/B/C (closed tie SW-12)", [p["loops"] for p in bad["phases"]], [1, 1, 1])
check("bad: islands A/B/C (B fuse on an A lateral)", [p["islands"] for p in bad["phases"]], [0, 1, 0])

island = run("feeder-island.yaml")
check("island: islands A/B/C (R-1011 left open)", [p["islands"] for p in island["phases"]], [1, 1, 1])
check("island: R-1011 load point cut off on every phase",
      all("R-1011" in p["islanded_nodes"] for p in island["phases"]), True)

check("rank and graph search agree, every fixture and phase",
      all(p["rank_matches_search"] for r in (normal, bad, island) for p in r["phases"]), True)

print(f"\n  topology: {11 - fails} passed, {fails} failed")
sys.exit(fails)
