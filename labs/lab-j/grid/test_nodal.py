#!/usr/bin/env python3
"""Pinned results for nodal.py (part 4). Exit code = number of failures."""
import os
import sys

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import nodal  # noqa: E402
import topology  # noqa: E402

fails = 0


def check(name, ok, got):
    global fails
    fails += not ok
    print(f"  {'PASS' if ok else 'FAIL'}  {name:58s} {got}")


normal_n = nodal.analyse(os.path.join(HERE, "feeder-normal.yaml"))
normal_t = topology.analyse(os.path.join(HERE, "feeder-normal.yaml"))

# 1. On a radial feeder the node method must agree with part 3, which solved the same
#    physics a different way (current law by itself, then the voltage law).
same_amps = all(abs(normal_n["phases"][k]["sections"][s["device"]] - s["amps"]) < 0.05
                for k in range(3) for s in normal_t["phases"][k]["sections"])
check("radial: section currents match part 3 (all phases)", same_amps, same_amps)
same_drop = all(abs(normal_n["phases"][k]["voltage_drop_pct"][n] - v) < 0.005
                for k in range(3) for n, v in normal_t["phases"][k]["voltage_drop_pct"].items())
check("radial: voltage drops match part 3 within 0.005 points", same_drop, same_drop)

bad = nodal.analyse(os.path.join(HERE, "feeder-bad.yaml"))
a = bad["phases"][0]
check("loop: one loop on each phase", [p["loops"] for p in bad["phases"]] == [1, 1, 1],
      [p["loops"] for p in bad["phases"]])

# 2. Hand check for the loop. With the tie closed, the two feeders are parallel paths from the
#    bus to one combined load. Treating the tie as a short, the split is a current divider.
m = yaml.safe_load(open(os.path.join(HERE, "feeder-bad.yaml")))
dev = {d["id"]: d for f in m["feeders"] for d in f["devices"]}
z1 = complex(*dev["R-1011"]["z_ohm"]) + nodal.Z_MIN   # CB-101 (0 ohm -> 0.001) + R-1011 section
z2 = complex(*dev["R-1021"]["z_ohm"]) + nodal.Z_MIN   # CB-102 + R-1021 section
total = dev["R-1011"]["load_a"] + dev["FU-1012"]["load_a"] + dev["R-1021"]["load_a"]   # 248 A
i1 = abs(total * z2 / (z1 + z2))
check(f"loop, phase A: CB-101 = current divider {i1:.1f} A", abs(a["sections"]["CB-101"] - i1) < 0.5,
      a["sections"]["CB-101"])
check("loop, phase A: CB-101 + CB-102 = 248 A of load",
      abs(a["sections"]["CB-101"] + a["sections"]["CB-102"] - total) < 0.2,
      a["sections"]["CB-101"] + a["sections"]["CB-102"])
check("loop, phase A: tie SW-12 carries 43.0 A", a["sections"]["SW-12"] == 43.0, a["sections"]["SW-12"])

# 3. Kirchhoff's laws hold on every phase of both feeders, loops included.
allp = normal_n["phases"] + bad["phases"]
check("Kirchhoff's current law: residual below 1e-6 A", all(p["kcl_residual"] < 1e-6 for p in allp),
      max(p["kcl_residual"] for p in allp))
check("Kirchhoff's voltage law around each loop: below 1e-6 V", all(p["kvl_residual"] < 1e-6 for p in allp),
      max(p["kvl_residual"] for p in allp))

# 4. The islanded part of phase B is left out, and part 3 names the same nodes.
t_bad = topology.analyse(os.path.join(HERE, "feeder-bad.yaml"))
check("islanded nodes match part 3 on every phase",
      all(bad["phases"][k]["islanded_nodes"] == t_bad["phases"][k]["islanded_nodes"] for k in range(3)),
      bad["phases"][1]["islanded_nodes"])

print(f"\n  nodal: {9 - fails} passed, {fails} failed")
sys.exit(fails)
