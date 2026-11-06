# Georeferencing by least squares

When you georeference an image in ArcGIS Pro, you click control points: a pixel in the image and the
surveyed coordinate of the same spot on the ground. Pro fits the transform by least squares and
reports an RMS error. `affine_fit.py` does that fit by hand for a first-order (affine) transform,
using the least-squares section of MIT 18.06 (Unit II: projections and least squares).

Each control point gives two equations, one for X and one for Y:

```
X = a*col + b*row + c
Y = d*col + e*row + f
```

Nine points give eighteen equations for six unknowns, so there's no exact answer. The least-squares
answer is the projection of the surveyed coordinates onto the column space of `A = [col, row, 1]`:

```
A^T A x_hat = A^T b      normal equations
e = b - A x_hat          error, perpendicular to every column of A (A^T e = 0)
```

## Results (synthetic data, seed 20261106)

The data are made up: a local grid in metres, a 3 cm-per-pixel image rotated 1.5 degrees, 2 cm of
survey error and half a pixel of picking error on each point. Nothing here is from an employer.

| | |
|---|---|
| Recovered pixel size | 3.001 cm (true 3.000) |
| Recovered rotation | 1.491 degrees (true 1.500) |
| RMS error on the 9 control points | 2.4 cm |
| RMS error on 3 points held back from the fit | 3.8 cm |
| QR, normal equations and numpy `lstsq` | agree to 1e-12 |
| `A^T e` (should be zero) | largest entry 1.6e-8 |

The held-back points are the honest number. The RMS that Pro reports is measured on the same
points the fit was built from, so it will always look a little better than the fit really is.

## Why centre the coordinates first

Solving the normal equations means working with `A^T A`, and its condition number is the square
of `A`'s. On raw pixel coordinates `cond(A)` is about 12,000 and `cond(A^T A)` about 150 million.
Subtracting the mean pixel position first brings `cond(A)` down to about 2,900. QR works on `A`
directly, which is why it's the safer method. All three agree here because the problem is small.

## One mistyped control point

If one easting is typed 5 m wrong, the RMS error jumps from 2.4 cm to 157 cm. Refitting without
each point in turn (leave-one-out) finds it: point 5 lands 5.00 m from the fit of the other eight.
While the bad point is still in the data it drags the fit for every other point, so the next
worst leave-one-out error is 1.08 m. The fix is to remove the blunder and refit, not to accept a
"good enough" RMS.

## Running it

`python3 affine_fit.py --check` prints the results and checks them: the methods agree, the error
is orthogonal to the columns, `P = A (A^T A)^-1 A^T` is a projection, the transform is recovered,
`cond(A^T A) = cond(A)^2`, and leave-one-out finds point 5. It runs in CI
(`.github/workflows/engineering.yml`).

Built with an AI coding assistant, like the rest of this repository. MIT 18.06 is on my study
plan, and this is where its least-squares unit meets the georeferencing that ArcGIS Pro does for you.
