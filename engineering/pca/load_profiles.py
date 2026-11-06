#!/usr/bin/env python3
"""Principal component analysis of daily load profiles.

Course material this follows:
  Imperial College London, Mathematics for Machine Learning: PCA (all four modules: statistics of
    datasets, inner products, orthogonal projections, PCA)
  DeepLearning.AI, Linear Algebra for Machine Learning and Data Science, week 4 (eigenvalues,
    covariance matrix, PCA)
  University of Michigan, Applied Machine Learning in Python, module 4 (dimensionality reduction,
    clustering)

A smart meter gives each customer 24 hourly readings a day, so every customer is a point in 24
dimensions. PCA finds the few directions in that space where customers actually differ.

The data are synthetic: 600 made-up customers of three kinds (residential with a morning bump and
an evening peak, commercial with a flat daytime load, and overnight EV charging), each with its own
size, a random shift of up to an hour, and noise. Each profile is divided by its own daily average
so PCA looks at the shape of the day, not the size of the customer.

What the script computes and checks:
  1. Covariance C = X^T X / (n - 1) of the centered data, and its eigenvectors (numpy eigh).
     The same answer from the SVD of X: eigenvalues = s^2 / (n - 1).
  2. Because every normalized profile sums to exactly 24, the data sit in a 23-dimensional slice
     of the 24-dimensional space, so the smallest eigenvalue must be zero.
  3. Keeping k components, the mean squared reconstruction error equals the sum of the eigenvalues
     left out. That is the theorem behind choosing k.
  4. The projection P = V_k V_k^T onto the principal subspace satisfies P^2 = P and P = P^T.
  5. A linear transformation of the data transforms the covariance as A^T C A. Checked by adding
     the 24 hours up into four 6-hour blocks.
  6. k-means (Lloyd's algorithm, written out) on the first two component scores, compared with the
     known customer types. PCA never saw the types.

Usage: load_profiles.py [--check]
"""
import itertools
import sys

import numpy as np

SEED = 20261106
N_PER_TYPE = 200
HOURS = np.arange(24)
TYPES = ["residential", "commercial", "EV overnight"]


def bump(center, width, hours=HOURS):
    """A smooth daily bump, wrapped around midnight."""
    d = np.minimum(np.abs(hours - center), 24 - np.abs(hours - center))
    return np.exp(-0.5 * (d / width) ** 2)


def make_profiles(rng):
    rows, labels = [], []
    for t in range(3):
        for _ in range(N_PER_TYPE):
            s = rng.uniform(-1.0, 1.0)                     # shift the day by up to an hour
            if t == 0:
                shape = 0.4 + 0.6 * bump(7.5 + s, 1.2) + 1.4 * bump(19 + s, 2.0)
            elif t == 1:
                shape = 0.3 + 1.5 * (bump(10 + s, 2.0) + bump(15 + s, 2.0))
            else:
                shape = 0.5 + 0.5 * bump(19 + s, 2.5) + 2.0 * bump(2 + s, 1.8)
            kw = rng.uniform(0.5, 30.0) * shape            # customer size
            kw = kw * (1 + rng.normal(0, 0.08, 24))        # meter-to-meter noise
            rows.append(np.clip(kw, 0.01, None))
            labels.append(t)
    X = np.array(rows)
    X = X / X.mean(axis=1, keepdims=True)                  # shape of the day: each row sums to 24
    return X, np.array(labels)


def pca(X):
    mu = X.mean(axis=0)
    Xc = X - mu
    C = Xc.T @ Xc / (len(X) - 1)
    lam, V = np.linalg.eigh(C)
    order = np.argsort(lam)[::-1]
    return mu, Xc, C, lam[order], V[:, order]


def kmeans(Z, k, rng, iters=100):
    best = None
    for _ in range(10):                                    # several random starts, keep the best
        cent = Z[rng.choice(len(Z), k, replace=False)]
        for _ in range(iters):
            d = ((Z[:, None, :] - cent[None, :, :]) ** 2).sum(axis=2)
            lab = d.argmin(axis=1)
            new = np.array([Z[lab == j].mean(axis=0) if np.any(lab == j) else cent[j] for j in range(k)])
            if np.allclose(new, cent):
                break
            cent = new
        inertia = float(((Z - cent[lab]) ** 2).sum())
        if best is None or inertia < best[0]:
            best = (inertia, lab)
    return best[1]


def bar(v, scale):
    n = int(round(abs(v) * scale))
    return ("+" if v >= 0 else "-") * min(n, 30)


def main():
    rng = np.random.default_rng(SEED)
    X, labels = make_profiles(rng)
    mu, Xc, C, lam, V = pca(X)
    r = {}

    # 1. eigh vs SVD
    s = np.linalg.svd(Xc, compute_uv=False)
    r["svd"] = float(np.max(np.abs(s**2 / (len(X) - 1) - lam)))
    r["orthonormal"] = float(np.max(np.abs(V.T @ V - np.eye(24))))

    # 2. rows sum to 24, so one direction has no variance at all
    r["rowsum"] = float(np.max(np.abs(X.sum(axis=1) - 24)))
    r["lam_min"] = float(lam[-1])
    r["lam_min_vec_is_ones"] = float(abs(abs(V[:, -1] @ np.ones(24)) / np.sqrt(24) - 1))

    # 3. reconstruction error = sum of the eigenvalues left out
    total = lam.sum()
    recon = []
    for k in range(1, 7):
        Vk = V[:, :k]
        Xhat = Xc @ Vk @ Vk.T
        mse = float(((Xc - Xhat) ** 2).sum() / (len(X) - 1))
        recon.append((k, lam[:k].sum() / total, mse, float(lam[k:].sum())))
    r["recon_gap"] = max(abs(m - left) for _, _, m, left in recon)

    # 4. projection matrix
    P = V[:, :2] @ V[:, :2].T
    r["proj"] = float(max(np.max(np.abs(P @ P - P)), np.max(np.abs(P - P.T))))

    # 5. covariance under a linear map: four 6-hour totals
    A = np.zeros((24, 4))
    for h in range(24):
        A[h, h // 6] = 1.0
    B = X @ A
    Bc = B - B.mean(axis=0)
    r["linmap"] = float(np.max(np.abs(Bc.T @ Bc / (len(B) - 1) - A.T @ C @ A)))

    # 6. k-means on the first two scores
    Z = Xc @ V[:, :2]
    found = kmeans(Z, 3, np.random.default_rng(SEED + 1))
    best_acc, best_map = 0.0, None
    for perm in itertools.permutations(range(3)):
        acc = float(np.mean(np.array(perm)[found] == labels))
        if acc > best_acc:
            best_acc, best_map = acc, perm
    mapped = np.array(best_map)[found]
    conf = np.zeros((3, 3), dtype=int)
    for t, f in zip(labels, mapped):
        conf[t, f] += 1
    r["kmeans_acc"] = best_acc

    print(f"  {len(X)} synthetic customers x 24 hourly readings, each scaled to its own daily average")
    print(f"    covariance eigenvalues vs SVD of the data: largest difference {r['svd']:.1e}")
    print(f"    eigenvectors orthonormal (V^T V = I) to {r['orthonormal']:.1e}")
    print("\n  Variance explained and reconstruction error (k components kept)")
    print("     k   cumulative   mean sq. error   sum of eigenvalues left out")
    for k, cum, mse, left in recon:
        print(f"    {k:2d}     {100 * cum:6.2f}%       {mse:9.5f}        {left:9.5f}")
    print(f"    error equals the left-out eigenvalues to {r['recon_gap']:.1e}")
    print(f"\n  Smallest eigenvalue {r['lam_min']:.1e}: every row sums to 24, so the data lie in 23 dimensions;")
    print(f"    its eigenvector is the all-ones direction to {r['lam_min_vec_is_ones']:.1e}")
    print(f"  Projection onto the first two components: P^2 = P and P = P^T to {r['proj']:.1e}")
    print(f"  Four 6-hour totals: covariance equals A^T C A to {r['linmap']:.1e}")

    print("\n  First two components by hour (+ above the average day, - below)")
    sc = 60
    for h in range(0, 24, 2):
        print(f"    {h:02d}:00  PC1 {V[h, 0]:+.2f} {bar(V[h, 0], sc):<20s} PC2 {V[h, 1]:+.2f} {bar(V[h, 1], sc)}")

    print("\n  k-means (k = 3) on the two component scores vs the customer types PCA never saw")
    print("                      " + "  ".join(f"{'cluster ' + str(j + 1):>10s}" for j in range(3)))
    for t in range(3):
        print(f"    {TYPES[t]:>16s}  " + "  ".join(f"{conf[t, j]:10d}" for j in range(3)))
    print(f"    agreement {100 * best_acc:.1f}%")

    if "--check" in sys.argv:
        bad = []
        if r["svd"] > 1e-9: bad.append("eigh and SVD disagree")
        if r["orthonormal"] > 1e-9: bad.append("eigenvectors not orthonormal")
        if r["rowsum"] > 1e-9 or abs(r["lam_min"]) > 1e-9: bad.append("smallest eigenvalue not zero")
        if r["lam_min_vec_is_ones"] > 1e-6: bad.append("null direction is not all-ones")
        if r["recon_gap"] > 1e-9: bad.append("reconstruction error != left-out eigenvalues")
        if r["proj"] > 1e-9: bad.append("P is not a projection")
        if r["linmap"] > 1e-9: bad.append("cov(XA) != A^T C A")
        if recon[1][1] < 0.6: bad.append("two components explain too little")
        if r["kmeans_acc"] < 0.9: bad.append("clusters do not match the types")
        print("\n  check:", "PASS" if not bad else f"FAIL {bad}")
        sys.exit(len(bad))


if __name__ == "__main__":
    main()
