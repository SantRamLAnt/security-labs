# PCA on daily load profiles

`load_profiles.py` runs principal component analysis on 600 made-up smart-meter customers, each
a day of 24 hourly readings. It follows Imperial College London's *Mathematics for Machine
Learning: PCA*, week 4 of DeepLearning.AI's *Linear Algebra for Machine Learning and Data
Science*, and the dimensionality reduction and clustering part of Michigan's *Applied Machine
Learning in Python*.

There are three kinds of customer: residential (a morning bump and an evening peak), commercial
(flat through the working day) and overnight EV charging. Each profile is divided by its own daily
average, so a big store and a small apartment with the same daily pattern look the same to PCA.

| components kept | variance explained | mean squared error | eigenvalues left out |
|---|---|---|---|
| 1 | 61.96% | 3.26444 | 3.26444 |
| 2 | 92.10% | 0.67819 | 0.67819 |
| 3 | 94.86% | 0.44072 | 0.44072 |

The last two columns are the same number. The error you make by keeping k components is exactly
the sum of the eigenvalues you drop, which is the theorem behind picking k. The first component
is daytime against night: positive from about 08:00 to 16:00 and negative overnight. The second
is the evening peak.

Other checks in the script:

- The covariance eigenvalues from `eigh` match the SVD of the data (s² / (n − 1)).
- Every scaled profile sums to 24, so the data sit in 23 dimensions and the smallest eigenvalue is
  zero. Its eigenvector is the all-ones direction.
- The projection onto the first two components satisfies P² = P and P = Pᵀ.
- Adding the hours into four 6-hour totals is a linear map A, and the covariance of the totals is
  AᵀCA.
- k-means (Lloyd's algorithm, written out) on the first two component scores puts all 600
  customers back with their type. PCA was never told the types. The made-up types are very
  distinct, so real meter data would not separate this cleanly.

`python3 load_profiles.py --check` runs it with checks. Synthetic data only. Built with an AI
coding assistant, like the rest of this repository.
