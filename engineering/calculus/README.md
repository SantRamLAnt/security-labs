# A spread-out load as a Riemann sum

`distributed_load.py` checks a standard rule of thumb from distribution engineering: if a
lateral's load is spread evenly along it instead of sitting at the far end, the voltage drop is
about half and the losses are about a third. Both numbers come from integrals, and the script
shows the discrete sums getting there, using Riemann sums from MIT 18.01 (Session 46).

Split the load into N equal pieces along N equal sections. Section k carries every piece past
it, so relative to putting the whole load at the end:

```
drop ratio   = (N + 1) / (2N)                  -> integral of (1 - x)   from 0 to 1 = 1/2
losses ratio = (N + 1)(2N + 1) / (6 N^2)       -> integral of (1 - x)^2 from 0 to 1 = 1/3
```

| N | drop ratio | loss ratio |
|---|---|---|
| 1 | 1.000 | 1.000 |
| 10 | 0.550 | 0.385 |
| 100 | 0.505 | 0.338 |
| 1000 | 0.5005 | 0.3338 |

The drop's error is exactly 1/(2N). Each sum is computed term by term with exact fractions,
in closed form, and by solving Kirchhoff's current law as a matrix the way Lab J does, and all
three agree. With synthetic numbers (60 A on a lateral with 0.9 ohm of resistance), the end-load
drop of 54 V becomes 27 V and the losses go from 3.24 kW to 1.08 kW.

`python3 distributed_load.py --check` runs it with checks. Built with an AI coding assistant,
like the rest of this repository.
