# LAB J: The grid as configuration. Network model and control-centre perimeter, gated as code
Self-directed lab · synthetic model · Terraform planned in my own subscription, never applied

## The idea in one sentence
Two things a grid operator should never change casually are the electrical network's normal
configuration and the perimeter around its control centre. Here both are written as files,
and CI refuses a bad change before a person has to catch it.

## Part 1: the distribution network model (`grid/`, `policy/grid.rego`)
A synthetic substation with two radial 13.8 kV feeders. The rules come from how a
distribution system actually works, not from a security catalogue:

| Rule | Electrical reason | Control |
|---|---|---|
| Every change carries a switching order and an approver | An unreviewed record edit is an unauthorised configuration change | NERC CIP-010-4 R1.2 · NIST CM-3, CM-5 |
| A tie between feeders is normally open | Closed, it parallels two sources: the feeder is no longer radial and protection assumptions break | operational baseline |
| One source breaker per feeder | A radial feeder has exactly one source | network model integrity |
| A device cannot carry a phase its upstream device lacks | A B-phase fuse cannot be fed from an A-phase lateral | phase connectivity |
| Downstream protection rated below upstream | Otherwise the upstream device may operate first and drop more customers than necessary | coordination screen |

These are screening rules on a synthetic model. They are **not** a protection coordination
study, a load flow, or switching authority.

## Part 2: the Electronic Security Perimeter (`infra/`, `policy/esp.rego`)
Corporate, intermediate-system and control-centre subnets in Azure (Terraform, azurerm v4).

| Rule | Control |
|---|---|
| Inbound to the control-centre zone only from the intermediate system | NERC CIP-005-7 R1.2, R2.1 · NIST SC-7, AC-17 |
| Every allow rule carries its reason | NERC CIP-005-7 R1.3 |
| No public IP in the control-centre zone | NERC CIP-005-7 R1.1 · NIST SC-7(4) |
| Deny-all inbound stated explicitly | NERC CIP-005-7 R1.3 · NIST SC-7(5) |

## Part 3: the feeder as a matrix (`grid/topology.py`)
The policy rules look at one device and the device above it. That works for catching a fuse
rated higher than its recloser, but it can't see the shape of the whole network. So I also
wrote each phase of the model as an incidence matrix. The nodes are the substation bus and
the far end of every device. Each closed device is a column with -1 where it starts and +1
where it ends.

Two numbers come straight out of the rank of that matrix:

- **islands = nodes - rank - 1**, the pieces of the feeder with no path back to the substation
- **loops = edges - rank**, the independent closed loops. A radial feeder has none, so every
  edge has to add one to the rank.

When a phase is radial, the matrix with the substation row removed is square and invertible,
and Kirchhoff's laws turn into two linear solves:

- current law, `A_r i = d`: the current in every line section, from the loads
- voltage law, `A_r^T v = z * i`: the voltage drop at every node, from the section impedances

| Fixture | What changed | Policy denials | What the matrix shows |
|---|---|---|---|
| `feeder-normal` | nothing | 0 | Radial on all three phases. CB-101 carries 158 / 142 / 120 A on A / B / C, at most 26% of its 600 A rating. Largest voltage drop 1.61%, at the end of the FU-1012 lateral |
| `feeder-bad` | five errors | 6 | A loop on every phase from the closed tie, and FU-1013 cut off on phase B because it hangs from an A-phase lateral |
| `feeder-island` | R-1011 recorded as open after maintenance | **0** | R-1011's load point and everything below it has no path to the substation, on all three phases |

The island fixture is the reason I built this. It's an ordinary record mistake, it passes
every policy rule, and the matrix catches it straight away.

How I know the numbers are right:

- The rank and a plain graph search have to agree on whether there are islands. If they
  ever disagree, the run fails.
- The currents from the matrix solve are compared against a simple walk down the tree that
  adds up the loads below each device. CB-101 on phase A should be 120 + 38 = 158 A, and the
  voltage drop at FU-1012 works out by hand to about 1.61%. Both are pinned in
  `grid/test_topology.py`.
- I broke the matrix on purpose (dropped the -1 from every edge) and 4 of the 11 tests
  failed. Then I put it back.

My first version had a bug of the kind Lab E is about. On phase C of the island fixture,
R-1011 is open and nothing below it carries phase C, so its node never made it into the
graph. Its 120 A load disappeared and phase C came back "radial". Every device's load point
is now a node whether the device is open or closed, and the island test pins it.

Limits: this is a per-phase linear model with constant-current loads at a 0.9 power factor
and no coupling between phases. It's a screening calculation on a synthetic model. A real
study would use an AC load flow.

The maths in this part: rank and nullity, solving linear systems, the transpose relationship
between the current and voltage equations, Kirchhoff's laws and complex impedance.

## Tests
`run-tests.sh` pins an exact denial count per policy fixture (0 / 6 / 0 / 0 / 5), then runs the
11 pinned matrix checks. A known-bad fixture that suddenly passes means a rule stopped
evaluating, which is the failure mode Lab E documents. Runs in GitHub Actions
(`.github/workflows/lab-j.yml`) and as a third stage of the Harness pipeline
(`.harness/security-gates.yaml`).
