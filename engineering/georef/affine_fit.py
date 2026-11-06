#!/usr/bin/env python3
"""Georeferencing a drone image by least squares (MIT 18.06, Unit II: projections and least squares).

When you georeference an image in ArcGIS Pro, you click control points: a pixel in the image and
the surveyed coordinate of the same spot on the ground. With six or more numbers to find and
more points than you strictly need, Pro fits the transform by least squares and reports an RMS
error. This script does that fit by hand for a first-order (affine) transform:

    X = a*col + b*row + c
    Y = d*col + e*row + f

Each control point gives one equation for X and one for Y. With n points, that's A x = b with
A an n x 3 matrix [col, row, 1], solved separately for (a, b, c) and (d, e, f). There are more
equations than unknowns, so there's no exact solution, and 18.06's answer is the projection:

    A^T A x_hat = A^T b             the normal equations
    p = A x_hat                     the closest point to b in the column space of A
    e = b - p,   A^T e = 0          the error is perpendicular to every column of A

The data are synthetic: a made-up local grid in metres, a 3 cm-per-pixel image rotated 1.5
degrees, control points with 2 cm survey error and half a pixel of picking error, and one
deliberately mistyped point. Three extra check points are held back from the fit to measure
how well it predicts points it never saw.

Usage: affine_fit.py [--check]
"""
import math
import sys

import numpy as np

SEED = 20261106
GSD = 0.03            # metres per pixel
ROT = math.radians(1.5)
ORIGIN = (5000.0, 2000.0)


def truth(col, row):
    """The real image-to-ground transform the fit is trying to recover."""
    x = ORIGIN[0] + GSD * (math.cos(ROT) * col + math.sin(ROT) * row)
    y = ORIGIN[1] + GSD * (math.sin(ROT) * col - math.cos(ROT) * row)   # rows count downward
    return x, y


def make_points(rng):
    pix = [(400, 300), (3600, 350), (7600, 420), (500, 3100), (4000, 2950), (7500, 3200),
           (300, 5600), (3900, 5800), (7700, 5500)]
    check_pix = [(2100, 1600), (5800, 4300), (1500, 4700)]

    def survey(c, r):
        x, y = truth(c, r)
        return x + rng.normal(0, 0.02), y + rng.normal(0, 0.02)     # 2 cm GPS error

    def pick(c, r):
        return c + rng.normal(0, 0.5), r + rng.normal(0, 0.5)       # half-pixel picking error

    gcp = [(*pick(c, r), *survey(c, r)) for c, r in pix]
    chk = [(*pick(c, r), *survey(c, r)) for c, r in check_pix]
    blunder = list(gcp[4])
    blunder[2] += 5.0                                                # a 5 m typo in one easting
    gcp_blunder = gcp[:4] + [tuple(blunder)] + gcp[5:]
    return np.array(gcp), np.array(gcp_blunder), np.array(chk)


def design(pts, centre=None):
    c, r = pts[:, 0], pts[:, 1]
    if centre is not None:
        c, r = c - centre[0], r - centre[1]
    return np.column_stack([c, r, np.ones(len(pts))])


def fit(pts, method="qr", centre=None):
    A = design(pts, centre)
    out = []
    for b in (pts[:, 2], pts[:, 3]):
        if method == "normal":
            x = np.linalg.solve(A.T @ A, A.T @ b)
        elif method == "qr":
            Q, R = np.linalg.qr(A)
            x = np.linalg.solve(R, Q.T @ b)
        else:
            x = np.linalg.lstsq(A, b, rcond=None)[0]
        out.append(x)
    return out


def residuals(pts, params, centre=None):
    A = design(pts, centre)
    return np.column_stack([pts[:, 2] - A @ params[0], pts[:, 3] - A @ params[1]])


def rms(res):
    return float(math.sqrt(np.mean(np.sum(res**2, axis=1))))


def leave_one_out(pts, centre):
    """Refit without each point and see how far that point lands from the others' fit."""
    out = []
    for k in range(len(pts)):
        rest = np.delete(pts, k, axis=0)
        prm = fit(rest, centre=centre)
        out.append(float(np.linalg.norm(residuals(pts[k:k + 1], prm, centre)[0])))
    return out


def main():
    rng = np.random.default_rng(SEED)
    gcp, gcp_bad, chk = make_points(rng)
    centre = gcp[:, :2].mean(axis=0)
    r = {}

    p_qr = fit(gcp, "qr", centre)
    p_ne = fit(gcp, "normal", centre)
    p_ls = fit(gcp, "lstsq", centre)
    r["agree"] = max(float(np.max(np.abs(p_qr[i] - p_ne[i]))) + float(np.max(np.abs(p_qr[i] - p_ls[i])))
                     for i in range(2))
    res = residuals(gcp, p_qr, centre)
    A = design(gcp, centre)
    r["orth"] = float(np.max(np.abs(A.T @ res)))
    r["rms"] = rms(res)
    r["check_rms"] = rms(residuals(chk, p_qr, centre))
    a, b, _ = p_qr[0]
    r["gsd"] = math.hypot(a, b)
    r["rot"] = math.degrees(math.atan2(p_qr[1][0], a))

    P = A @ np.linalg.solve(A.T @ A, A.T)
    r["proj"] = float(max(np.max(np.abs(P @ P - P)), np.max(np.abs(P - P.T))))

    raw = design(gcp)
    r["cond_raw"] = float(np.linalg.cond(raw))
    r["cond_raw_ne"] = float(np.linalg.cond(raw.T @ raw))
    r["cond_ctr"] = float(np.linalg.cond(A))

    p_bad = fit(gcp_bad, "qr", centre)
    r["rms_bad"] = rms(residuals(gcp_bad, p_bad, centre))
    loo = leave_one_out(gcp_bad, centre)
    r["loo_worst"] = int(np.argmax(loo)) + 1
    r["loo"] = loo
    r["loo_next"] = sorted(loo)[-2]

    print("  Affine fit, 9 control points (synthetic), centred coordinates")
    print(f"    QR, normal equations and numpy lstsq agree to {r['agree']:.1e} (largest parameter difference)")
    print(f"    recovered pixel size {100 * r['gsd']:.3f} cm (true {100 * GSD:.3f}),"
          f" rotation {r['rot']:.3f} deg (true {math.degrees(ROT):.3f})")
    print(f"    RMS error on the control points  {100 * r['rms']:.1f} cm")
    print(f"    RMS error on 3 held-back points  {100 * r['check_rms']:.1f} cm")
    print(f"    A^T e = 0 check: largest entry {r['orth']:.1e}")
    print(f"    projection matrix P: P^2 = P and P = P^T to {r['proj']:.1e}")
    print("\n  Why centre the coordinates first")
    print(f"    cond(A) on raw pixel coordinates    {r['cond_raw']:.3e}")
    print(f"    cond(A^T A), what the normal equations solve  {r['cond_raw_ne']:.3e}  (the square)")
    print(f"    cond(A) after centring              {r['cond_ctr']:.3e}")
    print("\n  One mistyped control point (5 m in one easting)")
    print(f"    RMS error jumps from {100 * r['rms']:.1f} cm to {100 * r['rms_bad']:.1f} cm")
    print(f"    leave-one-out: point {r['loo_worst']} lands {r['loo'][r['loo_worst'] - 1]:.2f} m from the"
          f" fit of the other eight; the next worst is {r['loo_next']:.2f} m")

    if "--check" in sys.argv:
        bad = []
        if r["agree"] > 1e-6: bad.append("methods disagree")
        if r["orth"] > 1e-6: bad.append("residual not orthogonal")
        if r["proj"] > 1e-9: bad.append("P not a projection")
        if abs(r["gsd"] - GSD) > 1e-4 or abs(r["rot"] - 1.5) > 0.01: bad.append("transform not recovered")
        if not (0.01 < r["rms"] < 0.05): bad.append("control RMS out of expected range")
        if not (r["check_rms"] < 0.06): bad.append("check-point RMS too high")
        if abs(r["cond_raw_ne"] / r["cond_raw"] ** 2 - 1) > 0.01: bad.append("cond(A^T A) != cond(A)^2")
        if r["loo_worst"] != 5: bad.append("leave-one-out did not find the mistyped point")
        print("\n  check:", "PASS" if not bad else f"FAIL {bad}")
        sys.exit(len(bad))


if __name__ == "__main__":
    main()
