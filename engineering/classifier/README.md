# Logistic regression and one hidden layer, written out

`material_model.py` estimates whether a gas main is metallic or plastic from its install year and
diameter. It follows weeks 2 and 3 of DeepLearning.AI's *Neural Networks and Deep Learning*,
gradient descent and Newton's method from DeepLearning.AI's *Calculus for Machine Learning and
Data Science*, backpropagation from Imperial's *Multivariate Calculus*, and the evaluation module
of Michigan's *Applied Machine Learning in Python*.

The 3,000 records are made up. The rules that generate them are in the script: cast iron and
steel before about 1970, plastic phased in over the 1970s, steel kept for mains 12 inches and
larger, and 3% of labels flipped to stand in for record errors. Nothing comes from any utility.

**Logistic regression, three ways.** Gradient descent needs 872 iterations. Newton's method,
using the Hessian XᵀSX/n, needs 8, and its gradient shrinks 4e-1, 1e-1, 4e-2, 1e-2, 1e-3, 5e-5,
5e-8, 6e-14. Both land on the same weights, and scikit-learn agrees to 2e-8. The gradient is
checked against finite differences.

**One hidden layer** (8 tanh units). Backpropagation is written out and checked against finite
differences (largest relative difference 3e-8).

**What I found.** On 900 held-out records both models put the mains in nearly the same order
(ROC AUC 0.942 and 0.938). The difference is in the probabilities:

| held-out group | actual share metallic | logistic | hidden layer |
|---|---|---|---|
| under 12 in, before 1968 | 0.97 | 0.92 | 0.97 |
| under 12 in, 1980 or later | 0.09 | 0.17 | 0.07 |
| 12 in and up, 1980 or later | 0.95 | 0.76 | 0.94 |

"Metallic" is roughly "old OR large", and a straight-line boundary can't draw an OR, so logistic
regression has to treat new large mains as partly plastic. AUC only measures order, so it misses
this. Log-loss shows it: 0.291 against 0.231 held out, and the hidden layer is lower on all five
cross-validation folds (mean 0.277 against 0.203).

Missing a metal main is the costly error, so the script also picks a threshold on the training
data for 95% recall and applies it to the held-out records. Recall came out at 0.944 and 0.931,
a little under the target. A threshold tuned on one set of data doesn't carry over exactly.

Features are scaled with training-set statistics only, so nothing leaks from the held-out records
into training.

`python3 material_model.py --check` runs it with checks. Built with an AI coding assistant, like
the rest of this repository.
