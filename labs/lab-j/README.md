# LAB J — The grid as configuration: network model and control-centre perimeter, gated as code
Self-directed lab · synthetic model · Terraform planned in my own subscription, never applied

## The idea in one sentence
Two things a grid operator must never change casually — the electrical network's normal
configuration and the perimeter around its control centre — written as files and refused
by policy in CI before a human has to catch the mistake.

## Part 1 — the distribution network model (`grid/`, `policy/grid.rego`)
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

## Part 2 — the Electronic Security Perimeter (`infra/`, `policy/esp.rego`)
Corporate, intermediate-system and control-centre subnets in Azure (Terraform, azurerm v4).

| Rule | Control |
|---|---|
| Inbound to the control-centre zone only from the intermediate system | NERC CIP-005-7 R1.2, R2.1 · NIST SC-7, AC-17 |
| Every allow rule carries its reason | NERC CIP-005-7 R1.3 |
| No public IP in the control-centre zone | NERC CIP-005-7 R1.1 · NIST SC-7(4) |
| Deny-all inbound stated explicitly | NERC CIP-005-7 R1.3 · NIST SC-7(5) |

## Tests
`run-tests.sh` pins an exact denial count per fixture (0 / 6 / 0 / 5). A known-bad fixture
that suddenly passes means a rule stopped evaluating — the failure mode Lab E documents.
Runs in GitHub Actions (`.github/workflows/lab-j.yml`) and as a third stage of the Harness
pipeline (`.harness/security-gates.yaml`).
