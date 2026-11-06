#!/usr/bin/env python3
"""LAB J, part 3: the feeder model as a matrix.

The policy rules in policy/grid.rego check one device at a time against the device above it.
This script looks at the whole network at once. Each phase of the model becomes a graph:
the substation bus and the far end of every device are nodes, and every closed device is an
edge from its upstream node to its own node. The graph is written as an incidence matrix A
(one row per node, one column per edge; +1 where an edge ends, -1 where it starts).

Two numbers fall out of A with no special cases in the code:

  islands = nodes - rank(A) - 1      parts of the network with no path back to the substation
  loops   = edges - rank(A)          independent closed loops; a radial feeder has none

When a phase is radial (one connected piece, no loops), A with the substation row removed is
square and invertible, and the circuit equations become two linear solves:

  Kirchhoff's current law  A_r i = d        current in every section, from the loads d
  Kirchhoff's voltage law  A_r^T v = z * i  voltage drop at every node, from section impedance z

Limits, stated once: this is a per-phase linear model with constant-current loads and no
mutual coupling between phases. It is a screening calculation on a synthetic model, not a
load flow or a protection study.

Usage: topology.py FEEDER.yaml [--json]
"""
import cmath
import json
import math
import sys

import numpy as np
import yaml

PF = 0.9  # assumed load power factor (lagging) for every load in the synthetic model


def phase_graph(model, phase):
    """Nodes and closed edges for one phase. Returns (nodes, edges, devices_by_id)."""
    root = model["substation"]
    devs = {d["id"]: d for f in model["feeders"] for d in f["devices"]}
    edges, points = [], set()
    for d in devs.values():
        if phase not in d["phases"]:
            continue
        if not d.get("ties_to"):
            # Every device's far end is a node on this phase even when the device is open.
            # Leaving it out would make its load vanish, and a missing load reads as "clean".
            points.add(d["id"])
        if d.get("normal") != "closed":
            continue
        tail = d["upstream"] or root
        head = d["ties_at"] if d.get("ties_to") else d["id"]
        edges.append((d["id"], tail, head))
    nodes = [root] + sorted((points | {n for _, t, h in edges for n in (t, h)}) - {root})
    return nodes, edges, devs


def incidence(nodes, edges):
    idx = {n: k for k, n in enumerate(nodes)}
    A = np.zeros((len(nodes), len(edges)))
    for j, (_, tail, head) in enumerate(edges):
        A[idx[tail], j] -= 1
        A[idx[head], j] += 1
    return A


def reachable(nodes, edges, root):
    """Plain graph search, used only to name the islanded nodes and to cross-check the rank."""
    adj = {n: set() for n in nodes}
    for _, t, h in edges:
        adj[t].add(h)
        adj[h].add(t)
    seen, todo = {root}, [root]
    while todo:
        for m in adj[todo.pop()] - seen:
            seen.add(m)
            todo.append(m)
    return seen


def analyse_phase(model, phase):
    nodes, edges, devs = phase_graph(model, phase)
    root = nodes[0]
    A = incidence(nodes, edges)
    r = int(np.linalg.matrix_rank(A)) if edges else 0
    islands = len(nodes) - r - 1
    loops = len(edges) - r
    dead = sorted(set(nodes) - reachable(nodes, edges, root))
    out = {"phase": phase, "nodes": len(nodes), "edges": len(edges), "rank": r,
           "islands": islands, "loops": loops, "islanded_nodes": dead,
           "radial": islands == 0 and loops == 0}
    # The rank and the graph search answer the same question two different ways. If they
    # ever disagree, the analysis is wrong and must not report a clean result.
    out["rank_matches_search"] = (len(dead) > 0) == (islands > 0)
    if not out["radial"]:
        return out

    # Kirchhoff's current law. Loads are phasors at the assumed power factor.
    Ar = A[1:, :]
    lag = cmath.rect(1, -math.acos(PF))
    d = np.array([devs[n].get("load_a", 0) * lag for n in nodes[1:]], dtype=complex)
    i = np.linalg.solve(Ar.astype(complex), d)

    # Kirchhoff's voltage law: the drop across each section is z * i, summed toward each node.
    z = np.array([complex(*devs[e[0]].get("z_ohm", [0, 0])) for e in edges])
    v = np.linalg.solve(Ar.T.astype(complex), z * i)

    vln = model["feeders"][0]["voltage_kv"] * 1000 / math.sqrt(3)
    sections = []
    for j, (dev, _, _) in enumerate(edges):
        amps = abs(i[j])
        rating = devs[dev].get("rating_a")
        sections.append({"device": dev, "amps": round(float(amps), 1),
                         "rating_a": rating,
                         "loading_pct": round(100 * amps / rating, 1) if rating else None})
    drops = {n: round(float(100 * (vln - abs(vln - v[k])) / vln), 3) for k, n in enumerate(nodes[1:])}
    out.update({"sections": sections, "voltage_drop_pct": drops,
                "kcl_residual": float(np.max(np.abs(Ar @ i - d)))})
    return out


def analyse(path):
    model = yaml.safe_load(open(path))
    return {"file": path, "phases": [analyse_phase(model, p) for p in "ABC"]}


def report(res):
    print(f"  {res['file']}")
    for p in res["phases"]:
        state = "radial" if p["radial"] else "NOT RADIAL"
        print(f"   phase {p['phase']}: {p['nodes']} nodes, {p['edges']} edges, rank {p['rank']}"
              f"  ->  islands {p['islands']}, loops {p['loops']}  [{state}]")
        if p["islanded_nodes"]:
            print(f"      no path to the substation: {', '.join(p['islanded_nodes'])}")
        if p["loops"]:
            print("      closed loop: two sources in parallel; the current equations have no single answer")
        for s in p.get("sections", []):
            load = f"  {s['loading_pct']:5.1f}% of {s['rating_a']} A" if s["rating_a"] else ""
            print(f"      {s['device']:8s} {s['amps']:6.1f} A{load}")
        if "voltage_drop_pct" in p:
            worst = max(p["voltage_drop_pct"].items(), key=lambda kv: kv[1])
            print(f"      largest voltage drop: {worst[1]:.2f}% at {worst[0]}")


if __name__ == "__main__":
    res = analyse(sys.argv[1])
    print(json.dumps(res, indent=1)) if "--json" in sys.argv else report(res)
