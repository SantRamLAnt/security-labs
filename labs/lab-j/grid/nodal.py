#!/usr/bin/env python3
"""LAB J, part 4: the node method, so a looped feeder has an answer too.

Part 3 (topology.py) solves Kirchhoff's current law with the incidence matrix alone. That only
works on a radial phase: with a loop, current can split between two paths, and the current law
by itself can't say how. The split depends on the impedance of each path.

The node method from MIT 6.002 (Lecture 3) settles it. Pick a reference node, write the current
law at every other node with each branch current written as (voltage difference) x (admittance),
and collect the result into one linear system:

    Y e = f        Y = M diag(y) M^T      (M = incidence matrix, nodes x edges; y = 1/z per edge)

In MIT 18.06's notation (Lecture 12, Graphs, Networks, Incidence Matrices) the incidence matrix is
written edges x nodes, so the same matrix appears as A^T C A. Here the reference node is the
substation bus, held at its nominal voltage, and the unknowns are the voltages at every other node.

Two checks come straight from that lecture:
  - Kirchhoff's current law: M i = d at every node (the loads).
  - Kirchhoff's voltage law around every loop. The loops are a basis for the null space of M:
    edge-current patterns that satisfy the current law with no load at all. Summing z * i around
    each one must give zero.

Same limits as part 3: per-phase linear model, constant-current loads at a 0.9 power factor,
no coupling between phases. A switch or breaker with no impedance in the model gets 0.001 ohm so
the matrix can be inverted; that's a busbar, and it moves voltage drop by thousandths of a percent.

Usage: nodal.py FEEDER.yaml [--json]
"""
import cmath
import json
import math
import os
import sys

import numpy as np
import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from topology import PF, incidence, phase_graph, reachable  # noqa: E402

Z_MIN = 0.001  # ohms, for devices modelled with no impedance (busbar, switch, breaker)


def null_space(M, tol=1e-9):
    """Basis for the null space of M, from the singular value decomposition."""
    if M.shape[1] == 0:
        return np.zeros((0, 0))
    _, s, vt = np.linalg.svd(M)
    rank = int((s > tol).sum())
    return vt[rank:].T  # columns span {c : M c = 0}


def solve_phase(model, phase):
    nodes, edges, devs = phase_graph(model, phase)
    root = nodes[0]
    live = reachable(nodes, edges, root)
    dead = sorted(set(nodes) - live)
    nodes = [n for n in nodes if n in live]
    edges = [e for e in edges if e[1] in live and e[2] in live]
    out = {"phase": phase, "islanded_nodes": dead}
    if not edges:
        out["loops"] = 0
        return out

    M = incidence(nodes, edges)                                   # nodes x edges
    z = np.array([complex(*(devs[d].get("z_ohm") or [0, 0])) for d, _, _ in edges])
    z = np.where(np.abs(z) < Z_MIN, Z_MIN, z)
    y = 1 / z
    Y = M @ np.diag(y) @ M.T                                      # A^T C A in 18.06's notation

    vln = model["feeders"][0]["voltage_kv"] * 1000 / math.sqrt(3)
    lag = cmath.rect(1, -math.acos(PF))
    d = np.array([0] + [devs[n].get("load_a", 0) * lag for n in nodes[1:]], dtype=complex)

    # Node method: the substation bus (row 0) is held at vln, every other node is unknown.
    # Current law at node k: sum over edges of y*(e_k - e_other) = -load_k (loads draw current out).
    Yrr, Yr0 = Y[1:, 1:], Y[1:, 0]
    e = np.empty(len(nodes), dtype=complex)
    e[0] = vln
    e[1:] = np.linalg.solve(Yrr, -d[1:] - Yr0 * vln)

    # Branch currents, positive from the upstream end (tail) to the downstream end (head).
    idx = {n: k for k, n in enumerate(nodes)}
    i = np.array([y[j] * (e[idx[t]] - e[idx[h]]) for j, (_, t, h) in enumerate(edges)])

    loops = null_space(M)
    kvl = [float(abs(np.sum(loops[:, k] * z * i))) for k in range(loops.shape[1])]

    out.update({
        "loops": loops.shape[1],
        "sections": {dev: round(float(abs(i[j])), 1) for j, (dev, _, _) in enumerate(edges)},
        "voltage_drop_pct": {n: round(float(100 * (vln - abs(e[k])) / vln), 3)
                             for k, n in enumerate(nodes) if k},
        "kcl_residual": float(np.max(np.abs(M[1:] @ i - d[1:]))),
        "kvl_residual": max(kvl) if kvl else 0.0,
    })
    return out


def analyse(path):
    model = yaml.safe_load(open(path))
    return {"file": path, "phases": [solve_phase(model, p) for p in "ABC"]}


def report(res):
    print(f"  {res['file']}  (node method)")
    for p in res["phases"]:
        loops = p.get("loops", 0)
        print(f"   phase {p['phase']}: loops {loops}"
              + (f", left out (no path to the substation): {', '.join(p['islanded_nodes'])}"
                 if p["islanded_nodes"] else ""))
        for dev, amps in p.get("sections", {}).items():
            print(f"      {dev:8s} {amps:6.1f} A")
        if "voltage_drop_pct" in p:
            worst = max(p["voltage_drop_pct"].items(), key=lambda kv: kv[1])
            print(f"      largest voltage drop {worst[1]:.2f}% at {worst[0]};"
                  f" KCL residual {p['kcl_residual']:.1e} A, KVL residual {p['kvl_residual']:.1e} V")


if __name__ == "__main__":
    r = analyse(sys.argv[1])
    print(json.dumps(r, indent=1)) if "--json" in sys.argv else report(r)
