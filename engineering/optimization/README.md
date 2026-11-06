# Economic dispatch and a Newton-Raphson power flow

`dispatch_and_power_flow.py` works two standard power-system problems with the calculus from
KAIST's *Applied Math for Materials Science and Engineering* (maxima and minima, Lagrange
multipliers, differentiating with respect to a parameter), Imperial's *Multivariate Calculus*
(Jacobian, Hessian, Taylor linearization, Newton-Raphson) and week 3 of DeepLearning.AI's
*Calculus for Machine Learning and Data Science*. All numbers are synthetic.

## Economic dispatch

Three generators with quadratic costs must supply a demand. With a Lagrange multiplier, the
optimum has every unit that isn't at a limit running where its marginal cost equals λ.

| demand | output (MW) | λ ($/MWh) | d(cost)/d(demand) |
|---|---|---|---|
| 450 MW | 264.8, 136.1, 49.1 | 21.178 | 21.178 |
| 800 MW | 400.0 (at max), 265.0, 135.0 | 23.240 | 23.240 |

The last column is a finite difference of the optimal total cost as demand moves 1 MW each way. It
equals λ, so λ is the cost of the next megawatt. A brute-force search over every split 0.1 MW
apart finds the same cost, and the Hessian diag(2c) is positive definite, so it's a minimum. At
800 MW the first unit hits its 400 MW limit, is held there, and the other two are re-solved.

## Power flow

Three buses: a slack bus at 1.0 per unit, a generator bus holding 1.02 per unit and putting out
60 MW, and a load of 110 MW and 40 Mvar. Newton-Raphson solves the nonlinear power balance by
linearizing it with the Jacobian at each step. The largest mismatch went 1.0, 3.7e-2, 9.7e-5,
7.7e-10, 1.9e-15. Each step roughly squares the error, which is quadratic convergence. The
analytic Jacobian matches finite differences, and Gauss-Seidel, a separate method, needs 16
iterations to reach the same answer: load bus at 0.9694 per unit and −3.17°, losses 3.03 MW.

The DC power flow keeps only the first-order Taylor terms (sin θ ≈ θ, |V| ≈ 1, no resistance).
Its line flows come within 2.3 MW of the full AC answer here, and it never sees the losses.

`python3 dispatch_and_power_flow.py --check` runs it with checks. Built with an AI coding
assistant, like the rest of this repository.
