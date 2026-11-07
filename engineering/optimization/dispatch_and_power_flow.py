#!/usr/bin/env python3
"""Two optimization problems from power systems: economic dispatch and a Newton-Raphson power flow.

Course material this follows:
  KAIST, Applied Math for Materials Science and Engineering, module 3 (maxima and minima, Lagrange
    multipliers) and module 2 (differentiating with respect to a parameter)
  Imperial College London, Mathematics for Machine Learning: Multivariate Calculus, modules 2, 4
    and 5 (the Jacobian and Hessian, Taylor series and linearisation, Newton-Raphson, Lagrange
    multipliers)
  DeepLearning.AI, Calculus for Machine Learning and Data Science, week 3 (Newton's method, the
    Hessian and concavity)

Part 1, economic dispatch. Three generators with quadratic fuel costs C_i(P) = a_i + b_i P + c_i P^2
must together supply a demand D. Minimizing total cost subject to P_1 + P_2 + P_3 = D with a
Lagrange multiplier gives b_i + 2 c_i P_i = lambda for every generator that isn't at a limit:
each runs where its marginal cost equals lambda. That's a linear system. Then:
  - check it against a brute-force search over every feasible split, 0.1 MW apart
  - check the Hessian (diag 2 c_i) is positive definite, so it's a minimum
  - differentiate total cost with respect to the demand (a parameter): the envelope theorem says
    d(cost)/dD = lambda, the cost of the next megawatt. In a market with no losses or congestion,
    that's the energy price.
  - raise demand until one unit hits its maximum, fix it there, and solve again.

Part 2, AC power flow on three buses. Bus 1 is the slack (1.0 per unit at angle 0), bus 2 is a
generator holding 1.02 per unit, bus 3 is a load. The unknowns are the angles at buses 2 and 3
and the voltage magnitude at bus 3. The power balance equations are nonlinear (sines, cosines,
products of voltages), so Newton-Raphson linearizes them with the Jacobian at each step:
  J dx = -mismatch
  - the analytic Jacobian is checked against finite differences
  - convergence is quadratic: the mismatch roughly squares at each step
  - the answer is checked against Gauss-Seidel, an independent and slower method
  - the "DC" power flow (first-order Taylor: sin t ~ t, cos t ~ 1, |V| ~ 1) is solved too, to see
    how far that linear approximation lands from the full answer

All numbers are synthetic, in per unit on a 100 MVA base.

Usage: dispatch_and_power_flow.py [--check]
"""
import sys

import numpy as np

# ---------------- Part 1: economic dispatch ----------------
#                 a ($/h)   b ($/MWh)   c ($/MW^2 h)   Pmin   Pmax
GENS = np.array([[500.0,    18.0,       0.0060,        50,    400],
                 [400.0,    19.0,       0.0080,        40,    300],
                 [200.0,    20.0,       0.0120,        20,    200]])


def cost(P):
    a, b, c = GENS[:, 0], GENS[:, 1], GENS[:, 2]
    return float(np.sum(a + b * P + c * P**2))


def dispatch(D):
    """Solve the Lagrange conditions; units that would break a limit are fixed at it and the rest re-solved."""
    b, c, lo, hi = GENS[:, 1], GENS[:, 2], GENS[:, 3], GENS[:, 4]
    fixed = {}
    while True:
        free = [i for i in range(3) if i not in fixed]
        n = len(free)
        # unknowns: P for each free unit, then lambda
        M = np.zeros((n + 1, n + 1)); rhs = np.zeros(n + 1)
        for row, i in enumerate(free):
            M[row, row] = 2 * c[i]; M[row, n] = -1; rhs[row] = -b[i]      # b_i + 2 c_i P_i - lambda = 0
        M[n, :n] = 1; rhs[n] = D - sum(fixed.values())                    # sum of P = D
        sol = np.linalg.solve(M, rhs)
        P = np.zeros(3)
        for row, i in enumerate(free):
            P[i] = sol[row]
        for i, v in fixed.items():
            P[i] = v
        lam = sol[n]
        broke = [i for i in free if P[i] > hi[i] + 1e-9 or P[i] < lo[i] - 1e-9]
        if not broke:
            return P, lam, sorted(fixed)
        for i in broke:
            fixed[i] = hi[i] if P[i] > hi[i] else lo[i]


def brute_force(D, step=0.1):
    lo, hi = GENS[:, 3], GENS[:, 4]
    p1 = np.arange(lo[0], hi[0] + step / 2, step)
    p2 = np.arange(lo[1], hi[1] + step / 2, step)
    P1, P2 = np.meshgrid(p1, p2, indexing="ij")
    P3 = D - P1 - P2
    ok = (P3 >= lo[2]) & (P3 <= hi[2])
    a, b, c = GENS[:, 0], GENS[:, 1], GENS[:, 2]
    tot = (a[0] + b[0] * P1 + c[0] * P1**2 + a[1] + b[1] * P2 + c[1] * P2**2 + a[2] + b[2] * P3 + c[2] * P3**2)
    tot = np.where(ok, tot, np.inf)
    k = np.unravel_index(np.argmin(tot), tot.shape)
    return float(tot[k]), np.array([P1[k], P2[k], P3[k]])


# ---------------- Part 2: Newton-Raphson power flow ----------------
#        from  to   r (pu)   x (pu)
LINES = [(0,   1,   0.01,    0.03),
         (0,   2,   0.04,    0.12),
         (1,   2,   0.03,    0.09)]
V1, V2_SET = 1.0, 1.02
P2_GEN = 0.60                     # bus 2 injects 60 MW
P3_LOAD, Q3_LOAD = 1.10, 0.40     # bus 3 draws 110 MW and 40 Mvar


def ybus():
    Y = np.zeros((3, 3), dtype=complex)
    for f, t, r, x in LINES:
        y = 1 / complex(r, x)
        Y[f, f] += y; Y[t, t] += y; Y[f, t] -= y; Y[t, f] -= y
    return Y


def injections(Y, x):
    th2, th3, v3 = x
    V = np.array([V1, V2_SET * np.exp(1j * th2), v3 * np.exp(1j * th3)])
    S = V * np.conj(Y @ V)
    return V, S


def mismatch(Y, x):
    _, S = injections(Y, x)
    return np.array([S[1].real - P2_GEN, S[2].real + P3_LOAD, S[2].imag + Q3_LOAD])


def jacobian(Y, x):
    """Analytic partial derivatives of [P2, P3, Q3] with respect to [theta2, theta3, |V3|]."""
    G, B = Y.real, Y.imag
    th = np.array([0.0, x[0], x[1]]); v = np.array([V1, V2_SET, x[2]])
    J = np.zeros((3, 3))

    def dP_dth(i, k):
        if i == k:
            return -sum(v[i] * v[m] * (G[i, m] * np.sin(th[i] - th[m]) - B[i, m] * np.cos(th[i] - th[m]))
                        for m in range(3) if m != i)
        return v[i] * v[k] * (G[i, k] * np.sin(th[i] - th[k]) - B[i, k] * np.cos(th[i] - th[k]))

    def dQ_dth(i, k):
        if i == k:
            return sum(v[i] * v[m] * (G[i, m] * np.cos(th[i] - th[m]) + B[i, m] * np.sin(th[i] - th[m]))
                       for m in range(3) if m != i)
        return -v[i] * v[k] * (G[i, k] * np.cos(th[i] - th[k]) + B[i, k] * np.sin(th[i] - th[k]))

    def dP_dv(i, k):
        if i == k:
            return 2 * v[i] * G[i, i] + sum(v[m] * (G[i, m] * np.cos(th[i] - th[m]) + B[i, m] * np.sin(th[i] - th[m]))
                                            for m in range(3) if m != i)
        return v[i] * (G[i, k] * np.cos(th[i] - th[k]) + B[i, k] * np.sin(th[i] - th[k]))

    def dQ_dv(i, k):
        if i == k:
            return -2 * v[i] * B[i, i] + sum(v[m] * (G[i, m] * np.sin(th[i] - th[m]) - B[i, m] * np.cos(th[i] - th[m]))
                                             for m in range(3) if m != i)
        return v[i] * (G[i, k] * np.sin(th[i] - th[k]) - B[i, k] * np.cos(th[i] - th[k]))

    J[0, 0], J[0, 1], J[0, 2] = dP_dth(1, 1), dP_dth(1, 2), dP_dv(1, 2)
    J[1, 0], J[1, 1], J[1, 2] = dP_dth(2, 1), dP_dth(2, 2), dP_dv(2, 2)
    J[2, 0], J[2, 1], J[2, 2] = dQ_dth(2, 1), dQ_dth(2, 2), dQ_dv(2, 2)
    return J


def newton(Y, tol=1e-12):
    x = np.array([0.0, 0.0, 1.0])                                  # flat start
    hist = [float(np.max(np.abs(mismatch(Y, x))))]
    for _ in range(20):
        x = x - np.linalg.solve(jacobian(Y, x), mismatch(Y, x))
        hist.append(float(np.max(np.abs(mismatch(Y, x)))))
        if hist[-1] < tol:
            break
    return x, hist


def gauss_seidel(Y, tol=1e-10, max_iter=10_000):
    V = np.array([V1, V2_SET, 1.0], dtype=complex)
    S3 = complex(-P3_LOAD, -Q3_LOAD)
    for it in range(1, max_iter + 1):
        old = V.copy()
        Q2 = (V[1] * np.conj(Y[1] @ V)).imag                       # PV bus: use the current Q
        V2 = (complex(P2_GEN, -Q2) / np.conj(V[1]) - Y[1, 0] * V[0] - Y[1, 2] * V[2]) / Y[1, 1]
        V[1] = V2_SET * V2 / abs(V2)                               # hold the magnitude
        V[2] = (np.conj(S3) / np.conj(V[2]) - Y[2, 0] * V[0] - Y[2, 1] * V[1]) / Y[2, 2]
        if np.max(np.abs(V - old)) < tol:
            return np.array([np.angle(V[1]), np.angle(V[2]), abs(V[2])]), it
    return np.array([np.angle(V[1]), np.angle(V[2]), abs(V[2])]), max_iter


def dc_flow():
    """First-order Taylor approximation: lossless lines, flat voltages, sin(t) ~ t."""
    Bp = np.zeros((3, 3))
    for f, t, r, x in LINES:
        Bp[f, f] += 1 / x; Bp[t, t] += 1 / x; Bp[f, t] -= 1 / x; Bp[t, f] -= 1 / x
    th = np.linalg.solve(Bp[1:, 1:], np.array([P2_GEN, -P3_LOAD]))
    return np.concatenate([[0.0], th])


def line_flows(theta_or_V, ac):
    out = []
    for f, t, r, x in LINES:
        if ac:
            V = theta_or_V
            y = 1 / complex(r, x)
            out.append(float((V[f] * np.conj((V[f] - V[t]) * y)).real))
        else:
            th = theta_or_V
            out.append(float((th[f] - th[t]) / x))
    return out


def main():
    r = {}
    print("  Part 1: economic dispatch (synthetic generators)")
    for D in (450.0, 800.0):
        P, lam, at_limit = dispatch(D)
        best, Pbf = brute_force(D)
        r[D] = {"gap": best - cost(P), "lam": lam, "P": P, "limit": at_limit}
        # envelope theorem: derivative of the optimal cost with respect to demand
        dC = (cost(dispatch(D + 1)[0]) - cost(dispatch(D - 1)[0])) / 2
        r[D]["dC"] = dC
        lims = (", unit " + " and ".join(str(i + 1) for i in at_limit) + " at its maximum") if at_limit else ""
        print(f"    demand {D:.0f} MW: P = {P[0]:.1f}, {P[1]:.1f}, {P[2]:.1f} MW{lims}")
        print(f"      lambda {lam:.3f} $/MWh; marginal cost of each running unit "
              + ", ".join(f"{GENS[i, 1] + 2 * GENS[i, 2] * P[i]:.3f}" for i in range(3) if i not in at_limit))
        print(f"      total {cost(P):,.2f} $/h; brute force over every 0.1 MW split {best:,.2f} $/h")
        print(f"      d(total cost)/d(demand) by finite difference {dC:.3f} $/MWh (lambda {lam:.3f})")
    H = np.diag(2 * GENS[:, 2])
    r["hess_min_eig"] = float(np.linalg.eigvalsh(H).min())
    print(f"    Hessian of total cost: diag(2c), smallest eigenvalue {r['hess_min_eig']:.4f} > 0, so a minimum")

    print("\n  Part 2: Newton-Raphson power flow, 3 buses (per unit, 100 MVA base)")
    Y = ybus()
    x, hist = newton(Y)
    eps = 1e-7
    Jn = np.column_stack([(mismatch(Y, x + eps * e) - mismatch(Y, x - eps * e)) / (2 * eps) for e in np.eye(3)])
    r["jac"] = float(np.max(np.abs(jacobian(Y, x) - Jn)))
    xgs, it_gs = gauss_seidel(Y)
    r["gs"] = float(np.max(np.abs(x - xgs)))
    r["iters"] = len(hist) - 1
    r["hist"] = hist
    print("    largest power mismatch by iteration: " + ", ".join(f"{h:.1e}" for h in hist))
    print(f"    analytic Jacobian vs finite differences: {r['jac']:.1e}")
    print(f"    bus 2 angle {np.degrees(x[0]):.3f} deg; bus 3 angle {np.degrees(x[1]):.3f} deg, voltage {x[2]:.4f} pu")
    print(f"    Gauss-Seidel took {it_gs} iterations and agrees to {r['gs']:.1e}")

    V, S = injections(Y, x)
    ac = line_flows(V, True)
    th_dc = dc_flow()
    dc = line_flows(th_dc, False)
    r["losses"] = float(S.real.sum())
    print(f"    slack bus supplies {100 * S[0].real:.1f} MW; losses {100 * r['losses']:.2f} MW")
    print("\n    Linearized (DC) flow vs full AC flow, MW sent from the first bus")
    for (f, t, _, _), a, d in zip(LINES, ac, dc):
        print(f"      line {f + 1}-{t + 1}:  AC {100 * a:7.2f}   DC {100 * d:7.2f}   difference {100 * (d - a):+.2f}")
    r["dc_err"] = max(abs(a - d) for a, d in zip(ac, dc))

    if "--check" in sys.argv:
        bad = []
        for D in (450.0, 800.0):
            if not (-1e-6 <= r[D]["gap"] < 0.5): bad.append(f"dispatch at {D} not optimal")  # grid can only tie or lose
            if abs(r[D]["dC"] - r[D]["lam"]) > 1e-6: bad.append(f"dC/dD != lambda at {D}")
            if abs(r[D]["P"].sum() - D) > 1e-9: bad.append(f"supply != demand at {D}")
        if r[450.0]["limit"] or not r[800.0]["limit"]: bad.append("limit case not exercised")
        if r["hess_min_eig"] <= 0: bad.append("Hessian not positive definite")
        if r["jac"] > 1e-6: bad.append("Jacobian disagrees with finite differences")
        if r["iters"] > 6: bad.append("Newton slower than expected")
        if not all(hist[k + 1] < hist[k] ** 1.5 for k in range(1, len(hist) - 2)): bad.append("not quadratic")
        if r["gs"] > 1e-8: bad.append("Gauss-Seidel disagrees")
        if not (0 < r["losses"] < 0.05): bad.append("losses out of range")
        if not (r["dc_err"] < 0.05): bad.append("DC approximation too far off")
        print("\n  check:", "PASS" if not bad else f"FAIL {bad}")
        sys.exit(len(bad))


if __name__ == "__main__":
    main()
