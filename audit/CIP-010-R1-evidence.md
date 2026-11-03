# CIP-010-4 R1 — configuration change management evidence
Generated 2026-11-03 02:28 UTC from `git` and GitHub Actions by `ci/cip010_evidence.py` at commit `7c29304`.
Self-directed lab repository, synthetic systems. Format follows the questions a CIP-010 R1 audit asks.

## R1.1 — the baseline
The baseline is the content of these 18 files at `7c29304`, version-controlled; any deviation is a diff.

| File | Blob |
|---|---|
| `.github/workflows/lab-d-cluster.yml` | `bfa0f6cedc` |
| `.github/workflows/lab-j.yml` | `0355fc713d` |
| `.github/workflows/security-gates.yml` | `17f0e6666d` |
| `.gitleaksignore` | `b084bebd7c` |
| `.harness/security-gates.yaml` | `2267ca481a` |
| `ci/run-gates.sh` | `ac69727db2` |
| `infra/main.tf` | `e370e2e602` |
| `k8s/manifests/insecure-deployment.yaml` | `9849ad7a58` |
| `k8s/manifests/secure-deployment.yaml` | `5b9a084bf3` |
| `k8s/policies/kyverno-baseline.yaml` | `43794ae356` |
| `labs/lab-j/grid/feeder-bad.yaml` | `7ded48d1d2` |
| `labs/lab-j/grid/feeder-normal.yaml` | `b1d388acc5` |
| `labs/lab-j/infra/esp-insecure/main.tf` | `dd0cd53c54` |
| `labs/lab-j/infra/esp-secure/main.tf` | `f73d8aade2` |
| `labs/lab-j/policy/esp.rego` | `fec78c4386` |
| `labs/lab-j/policy/grid.rego` | `3683e21077` |
| `policy/storage.rego` | `52ccc47c33` |
| `policy/storage_hcl.rego` | `17c0f790cb` |

## R1.2 — every change to the baseline: who, when, what, and whether it passed the gates
| Commit | When (UTC) | Author | Signed | Change | Baseline files | Security gates |
|---|---|---|---|---|---|---|
| [`29132fc`](https://github.com/SantRamLAnt/security-labs/commit/29132fc) | 2026-10-31 15:51 | Luis Santiago-Ramirez | no | Lab E: pipeline as handed over (before review) | 6 | [Security Gates: failure](https://github.com/SantRamLAnt/security-labs/actions/runs/41216835426) |
| [`508b684`](https://github.com/SantRamLAnt/security-labs/commit/508b684) | 2026-10-31 16:00 | Luis Santiago-Ramirez | no | Lab E: fix three gates that passed without evaluating anything | 2 | [Security Gates: failure](https://github.com/SantRamLAnt/security-labs/actions/runs/41217514129) |
| [`6a672e3`](https://github.com/SantRamLAnt/security-labs/commit/6a672e3) | 2026-10-31 16:02 | Luis Santiago-Ramirez | no | Lab E: publish each gate's verbatim output to the run summary | 1 | [Security Gates: failure](https://github.com/SantRamLAnt/security-labs/actions/runs/41217744686) |
| [`279eb9b`](https://github.com/SantRamLAnt/security-labs/commit/279eb9b) | 2026-10-31 16:07 | Luis Santiago-Ramirez | no | Lab E: remediate every finding from the red run | 2 | [Security Gates: success](https://github.com/SantRamLAnt/security-labs/actions/runs/41218112892) |
| [`93a4441`](https://github.com/SantRamLAnt/security-labs/commit/93a4441) | 2026-10-31 16:10 | Luis Santiago-Ramirez | no | Lab D: run the admission policies on a real cluster (kind in CI) | 2 | [Security Gates: success](https://github.com/SantRamLAnt/security-labs/actions/runs/41218412807) · [Lab D · Live admission control: success](https://github.com/SantRamLAnt/security-labs/actions/runs/41218412543) |
| [`698aaa5`](https://github.com/SantRamLAnt/security-labs/commit/698aaa5) | 2026-10-31 16:29 | Luis Santiago-Ramirez | no | Lab E: portable gate runner and a Harness pipeline that tests the gates | 2 | [Security Gates: success](https://github.com/SantRamLAnt/security-labs/actions/runs/41219928253) |
| [`4878277`](https://github.com/SantRamLAnt/security-labs/commit/4878277) | 2026-10-31 19:46 | Luis Santiago-Ramirez | no | Lab J: grid network model and control-centre perimeter as code, with exact-count policy tests | 8 | [Lab J · Grid model and perimeter policy: success](https://github.com/SantRamLAnt/security-labs/actions/runs/41235803693) · [Security Gates: success](https://github.com/SantRamLAnt/security-labs/actions/runs/41235803437) |
| [`7c29304`](https://github.com/SantRamLAnt/security-labs/commit/7c29304) | 2026-11-02 21:27 | Luis Antonio Santiago-Ramirez | no | Finding 4, and a preventive image redaction check in Gates 0 and 1 (#10) | 1 | [Security Gates: success](https://github.com/SantRamLAnt/security-labs/actions/runs/41566249027) · [pages-build-deployment: success](https://github.com/SantRamLAnt/security-labs/actions/runs/41566248427) |

8 baseline changes. 3 failed the security gates. All three are the Lab E story (the pipeline as handed over, then the gates turning red on planted findings), and `279eb9b` remediated every finding.

## R1.4 / R1.5 — security controls verified before the change is accepted
Every push runs the blocking gates (secrets over full history, Checkov, Conftest/OPA, Semgrep, Trivy) and the
policy self-tests. Lab A and Lab J configurations were also planned against a real Azure subscription before acceptance.

## Branch protection on `main`, read live from the GitHub API
- Pull request required: **yes** · approvals required: 0
- Required status checks (strict, branch must be up to date): `Gate 4 · Dependencies`, `Gate 0 · Policy and scanner self-test`, `Gate 1 · Secret scanning (full history)`, `Gate 2 · Infrastructure as code`, `Gate 3 · Static analysis`
- Applies to administrators: **yes** · signed commits required: **no**

## Findings an auditor would raise — stated, not hidden
1. **No independent approval.** One person authors and accepts every change. Branch protection can require a second
   reviewer, but a one-person repository cannot satisfy it; in a team this is the separation-of-duties control for R1.2. **Open.**
2. **Unsigned commits** (8 of 8). Required signing makes authorship provable. **Open.**
3. **Failed changes could reach `main`.** True for the history above. **Fixed:** every change now needs a pull request with all
   five gates passing, with no administrator bypass — the gate is preventive, not just detective.
4. **Published identifiers, redacted after the fact.** A test service principal's client and object IDs, a role-assignment
   ID and the public IP address I worked from were visible in two published screenshots (Lab C, Lab I) and are still in this
   repository's history. They are identifiers, not credentials: there is nothing to rotate and they grant no access on their own.
   The history is deliberately not rewritten, because this package is generated from it and a force-push would invalidate every
   commit hash it cites. The correct order was to redact before publishing, not after. Same lesson as Gate 1: removing something
   after the fact is a detective control, not a preventive one. **Open in history, by decision.** **Preventive control in place:** Gate 1 runs OCR over every published image and fails on an identifier; Gate 0 proves it still catches one.
