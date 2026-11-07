#!/usr/bin/env python3
"""Logistic regression and a one-hidden-layer network, written out in NumPy.

Course material this follows:
  DeepLearning.AI, Neural Networks and Deep Learning, week 2 (logistic regression as a neural
    network, vectorization, gradient descent) and week 3 (one hidden layer, backpropagation,
    random initialization)
  DeepLearning.AI, Calculus for Machine Learning and Data Science, weeks 2 and 3 (gradient descent,
    Newton's method, the Hessian)
  Imperial College London, Mathematics for Machine Learning: Multivariate Calculus, module 3
    (multivariate chain rule, backpropagation)
  University of Michigan, Applied Machine Learning in Python, modules 2 and 3 (feature scaling,
    logistic regression, cross-validation, confusion matrices, precision-recall and ROC curves,
    choosing a threshold for the metric that matters)
  DeepLearning.AI, Probability and Statistics for Machine Learning, week 3 (maximum likelihood:
    log-loss is the negative log-likelihood of a Bernoulli model)

The problem: gas distribution records sometimes have the pipe material missing, and federal
integrity rules (49 CFR 192.1007) make operators deal with unknowns. Install year and diameter say
a lot about material. Here a model estimates whether a main is metallic (cast iron or steel) or
plastic from those two fields.

All records are made up. The rules that generate them are written below and are rough industry
history (cast iron and steel before about 1970, plastic phased in over the 1970s, steel kept for large mains),
with 3% of labels flipped to stand in for record errors. Nothing here comes from or describes any
utility's data.

Metallic is roughly "installed before the mid-1970s OR 12 inches and larger". A straight-line
boundary in (year, diameter) can't draw an OR, so logistic regression should do worse than a
network with a hidden layer. What I found: both models put the mains in nearly the same order
(ROC AUC about 0.94), but logistic regression gets the probabilities wrong for one group, large
mains installed after 1980, which it has to treat as half old and half new. AUC only measures the
order, so the difference shows up in log-loss and in a table of predicted vs actual by group.

Usage: material_model.py [--check]
"""
import sys

import numpy as np

SEED = 20261106
DIAMETERS = np.array([2, 3, 4, 6, 8, 12, 16])


def make_records(rng, n=3000):
    year = rng.integers(1900, 2021, n)
    diam = rng.choice(DIAMETERS, n, p=[0.2, 0.12, 0.18, 0.16, 0.12, 0.12, 0.1])
    p_plastic = np.clip((year - 1968) / 10, 0, 1) * 0.95          # plastic phases in 1968 to 1978
    p_plastic = np.where(diam >= 12, 0.05 * p_plastic, p_plastic)  # big mains stay steel
    metallic = (rng.random(n) >= p_plastic).astype(float)
    flip = rng.random(n) < 0.03                                    # record errors
    metallic[flip] = 1 - metallic[flip]
    return np.column_stack([year, diam]).astype(float), metallic


def sigmoid(z):
    return 1 / (1 + np.exp(-z))


def log_loss(p, y):
    p = np.clip(p, 1e-12, 1 - 1e-12)
    return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))


# ---------- logistic regression ----------

def lr_grad(w, X, y):
    return X.T @ (sigmoid(X @ w) - y) / len(y)


def lr_gradient_descent(X, y, alpha=1.0, tol=1e-7, max_iter=200_000):
    w = np.zeros(X.shape[1])
    for it in range(1, max_iter + 1):
        g = lr_grad(w, X, y)
        w -= alpha * g
        if np.linalg.norm(g) < tol:
            return w, it
    return w, max_iter


def lr_newton(X, y, tol=1e-12, max_iter=50):
    w = np.zeros(X.shape[1])
    steps = []
    for it in range(1, max_iter + 1):
        p = sigmoid(X @ w)
        g = X.T @ (p - y) / len(y)
        H = (X * (p * (1 - p))[:, None]).T @ X / len(y)            # Hessian = X^T S X / n
        w = w - np.linalg.solve(H, g)
        steps.append(float(np.linalg.norm(g)))
        if steps[-1] < tol:
            return w, it, steps
    return w, max_iter, steps


# ---------- one hidden layer ----------

def nn_init(rng, n_in, n_hidden):
    return {"W1": rng.normal(0, 0.5, (n_in, n_hidden)), "b1": np.zeros(n_hidden),
            "W2": rng.normal(0, 0.5, n_hidden), "b2": 0.0}


def nn_forward(p, X):
    A1 = np.tanh(X @ p["W1"] + p["b1"])
    return A1, sigmoid(A1 @ p["W2"] + p["b2"])


def nn_backward(p, X, y):
    A1, A2 = nn_forward(p, X)
    n = len(y)
    dZ2 = (A2 - y) / n                                             # chain rule through sigmoid + log-loss
    dZ1 = np.outer(dZ2, p["W2"]) * (1 - A1**2)                     # back through tanh
    return {"W1": X.T @ dZ1, "b1": dZ1.sum(axis=0), "W2": A1.T @ dZ2, "b2": float(dZ2.sum())}


def nn_train(X, y, rng, n_hidden=8, alpha=1.0, epochs=6000):
    p = nn_init(rng, X.shape[1], n_hidden)
    for _ in range(epochs):
        g = nn_backward(p, X, y)
        for k in p:
            p[k] = p[k] - alpha * g[k]
    return p


def nn_loss(p, X, y):
    return log_loss(nn_forward(p, X)[1], y)


def gradient_check(f, params, analytic, eps=1e-6):
    """Largest relative difference between backprop and centered finite differences."""
    worst = 0.0
    for k, v in params.items():
        arr = np.atleast_1d(np.array(v, dtype=float))
        num = np.zeros_like(arr)
        for idx in np.ndindex(arr.shape):
            for sgn in (+1, -1):
                pert = arr.copy()
                pert[idx] += sgn * eps
                q = dict(params)
                q[k] = pert if np.ndim(v) else float(pert[0])
                num[idx] += sgn * f(q) / (2 * eps)
        a = np.atleast_1d(analytic[k])
        worst = max(worst, float(np.max(np.abs(a - num) / np.maximum(1e-8, np.abs(a) + np.abs(num)))))
    return worst


# ---------- evaluation ----------

def auc(score, y):
    """Area under the ROC curve as the chance a random positive outranks a random negative."""
    order = np.argsort(score)
    ranks = np.empty(len(score))
    ranks[order] = np.arange(1, len(score) + 1)
    for s in np.unique(score):                                     # average ranks for ties
        m = score == s
        ranks[m] = ranks[m].mean()
    pos = y == 1
    n1, n0 = pos.sum(), (~pos).sum()
    return float((ranks[pos].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


def confusion(score, y, thr):
    pred = score >= thr
    tp = int(np.sum(pred & (y == 1))); fp = int(np.sum(pred & (y == 0)))
    fn = int(np.sum(~pred & (y == 1))); tn = int(np.sum(~pred & (y == 0)))
    return tp, fp, fn, tn


def threshold_for_recall(score, y, target):
    for thr in np.sort(np.unique(score))[::-1]:
        tp, fp, fn, tn = confusion(score, y, thr)
        if tp / (tp + fn) >= target:
            return float(thr)
    return 0.0


def standardize(train, *others):
    mu, sd = train.mean(axis=0), train.std(axis=0)                 # training rows only: no leakage
    return [(a - mu) / sd for a in (train,) + others]


def with_bias(X):
    return np.column_stack([np.ones(len(X)), X])


def main():
    rng = np.random.default_rng(SEED)
    X, y = make_records(rng)
    idx = rng.permutation(len(y))
    tr, te = idx[:2100], idx[2100:]
    Xtr, Xte = standardize(X[tr], X[te])
    ytr, yte = y[tr], y[te]
    r = {}

    print(f"  {len(y)} synthetic main records (install year, diameter); {100 * y.mean():.1f}% metallic")
    print(f"  70/30 split: {len(tr)} to train, {len(te)} held out; scaled with training means only\n")

    # Logistic regression three ways
    Btr, Bte = with_bias(Xtr), with_bias(Xte)
    w_gd, it_gd = lr_gradient_descent(Btr, ytr)
    w_nt, it_nt, steps = lr_newton(Btr, ytr)
    r["gd_vs_newton"] = float(np.max(np.abs(w_gd - w_nt)))
    try:
        from sklearn.linear_model import LogisticRegression
        sk = LogisticRegression(C=np.inf, tol=1e-12, max_iter=10_000).fit(Xtr, ytr)   # C=inf: no penalty
        w_sk = np.concatenate([sk.intercept_, sk.coef_[0]])
        r["sk"] = float(np.max(np.abs(w_sk - w_nt)))
    except ImportError:
        r["sk"] = None
    g_an = {"w": lr_grad(w_nt * 0.5, Btr, ytr)}
    r["lr_gradcheck"] = gradient_check(lambda q: log_loss(sigmoid(Btr @ q["w"]), ytr), {"w": w_nt * 0.5}, g_an)

    print("  Logistic regression (log-loss = Bernoulli negative log-likelihood)")
    print(f"    gradient descent: {it_gd:,} iterations to a gradient below 1e-7")
    print(f"    Newton's method:  {it_nt} iterations; gradient size per step: "
          + ", ".join(f"{s:.0e}" for s in steps))
    print(f"    the two agree to {r['gd_vs_newton']:.1e}"
          + (f"; scikit-learn agrees to {r['sk']:.1e}" if r["sk"] is not None else ""))
    print(f"    gradient check (finite differences): largest relative difference {r['lr_gradcheck']:.1e}")

    # One hidden layer
    p0 = nn_init(np.random.default_rng(SEED + 2), 2, 8)
    r["nn_gradcheck"] = gradient_check(lambda q: nn_loss(q, Xtr, ytr), p0, nn_backward(p0, Xtr, ytr))
    net = nn_train(Xtr, ytr, np.random.default_rng(SEED + 2))
    print("\n  One hidden layer (8 tanh units, sigmoid output), backpropagation written out")
    print(f"    gradient check: largest relative difference {r['nn_gradcheck']:.1e}")

    s_lr = sigmoid(Bte @ w_nt)
    s_nn = nn_forward(net, Xte)[1]
    r["auc_lr"], r["auc_nn"] = auc(s_lr, yte), auc(s_nn, yte)
    try:
        from sklearn.metrics import roc_auc_score
        r["auc_sk"] = max(abs(roc_auc_score(yte, s_lr) - r["auc_lr"]), abs(roc_auc_score(yte, s_nn) - r["auc_nn"]))
    except ImportError:
        r["auc_sk"] = None

    print(f"\n  Held-out records ({len(te)})        logistic   hidden layer")
    print(f"    log-loss                         {log_loss(s_lr, yte):.3f}      {log_loss(s_nn, yte):.3f}")
    print(f"    ROC AUC                          {r['auc_lr']:.3f}      {r['auc_nn']:.3f}"
          + (f"   (matches scikit-learn to {r['auc_sk']:.0e})" if r["auc_sk"] is not None else ""))
    for name, s in (("logistic", s_lr), ("hidden layer", s_nn)):
        tp, fp, fn, tn = confusion(s, yte, 0.5)
        print(f"    {name:>12s} at 0.5:  TP {tp}  FP {fp}  FN {fn}  TN {tn}  "
              f"precision {tp / (tp + fp):.3f}  recall {tp / (tp + fn):.3f}")

    # Where a straight line falls short: probabilities by group (calibration)
    yr, dm = X[te, 0], X[te, 1]
    groups = [("under 12 in, before 1968", (dm < 12) & (yr < 1968)),
              ("under 12 in, 1980 or later", (dm < 12) & (yr >= 1980)),
              ("12 in and up, before 1968", (dm >= 12) & (yr < 1968)),
              ("12 in and up, 1980 or later", (dm >= 12) & (yr >= 1980))]
    print("\n  Held-out mains by group: share actually metallic vs average predicted probability")
    print("                                    n   actual   logistic   hidden layer")
    r["calib"] = {}
    for name, m in groups:
        r["calib"][name] = (float(yte[m].mean()), float(s_lr[m].mean()), float(s_nn[m].mean()))
        print(f"    {name:>28s}  {m.sum():4d}   {yte[m].mean():.2f}     {s_lr[m].mean():.2f}       {s_nn[m].mean():.2f}")

    # The error that matters: calling a metal main plastic. Pick the threshold on training data.
    print("\n  Threshold chosen on training data for 95% recall of metallic mains, applied to held-out")
    r["thr"] = {}
    for name, s_tr, s_te in (("logistic", sigmoid(Btr @ w_nt), s_lr),
                             ("hidden layer", nn_forward(net, Xtr)[1], s_nn)):
        thr = threshold_for_recall(s_tr, ytr, 0.95)
        tp, fp, fn, tn = confusion(s_te, yte, thr)
        r["thr"][name] = (tp / (tp + fn), tp / (tp + fp), fp)
        print(f"    {name:>12s}: threshold {thr:.3f}, recall {tp / (tp + fn):.3f}, precision {tp / (tp + fp):.3f}, "
              f"plastic mains flagged as metal {fp}")

    # 5-fold cross-validation
    folds = np.array_split(np.random.default_rng(SEED + 3).permutation(len(y)), 5)
    cv = {"logistic": [], "hidden layer": []}
    for k in range(5):
        te_k = folds[k]
        tr_k = np.concatenate([folds[j] for j in range(5) if j != k])
        a, b = standardize(X[tr_k], X[te_k])
        w, _, _ = lr_newton(with_bias(a), y[tr_k])
        cv["logistic"].append(log_loss(sigmoid(with_bias(b) @ w), y[te_k]))
        n = nn_train(a, y[tr_k], np.random.default_rng(SEED + 10 + k), epochs=3000)
        cv["hidden layer"].append(log_loss(nn_forward(n, b)[1], y[te_k]))
    print("\n  5-fold cross-validation, log-loss per fold (lower is better)")
    for name, v in cv.items():
        print(f"    {name:>12s}: " + "  ".join(f"{a:.3f}" for a in v) + f"   mean {np.mean(v):.3f}")
    r["cv"] = {k: float(np.mean(v)) for k, v in cv.items()}
    r["cv_folds_won"] = int(sum(b < a for a, b in zip(cv["logistic"], cv["hidden layer"])))

    if "--check" in sys.argv:
        bad = []
        if r["gd_vs_newton"] > 1e-4: bad.append("gradient descent and Newton disagree")
        if r["sk"] is not None and r["sk"] > 1e-3: bad.append("scikit-learn disagrees")
        if it_nt > 15: bad.append("Newton too slow")
        if r["lr_gradcheck"] > 1e-6 or r["nn_gradcheck"] > 1e-5: bad.append("gradient check failed")
        if r["auc_sk"] is not None and r["auc_sk"] > 1e-9: bad.append("AUC differs from scikit-learn")
        if not log_loss(s_nn, yte) < log_loss(s_lr, yte): bad.append("hidden layer log-loss not lower")
        if r["cv_folds_won"] < 4: bad.append("hidden layer not better on at least 4 of 5 folds")
        big_new = r["calib"]["12 in and up, 1980 or later"]
        if not abs(big_new[2] - big_new[0]) < abs(big_new[1] - big_new[0]): bad.append("calibration not better")
        print("\n  check:", "PASS" if not bad else f"FAIL {bad}")
        sys.exit(len(bad))


if __name__ == "__main__":
    main()
