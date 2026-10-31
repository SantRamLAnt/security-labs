# security-labs

Self-directed cloud, DevSecOps and AI security labs, built against a
Cloud / DevSecOps / AI Security analyst job description at a regional grid operator.

**What this is:** practice, on my own GitHub account and my own Azure subscription,
on my own time, with synthetic data. **What it is not:** professional security
experience, or anything touching an employer's systems. Nothing in this repository
was ever pointed at a system I don't own.

Every planted "secret" here is fake: either AWS's published documentation example key
or a random string generated for the lab. None is, or ever was, a real credential.

## Layout

| Path | What |
|---|---|
| `.github/workflows/security-gates.yml` | Lab E: five blocking CI gates (Gate 0 tests the policies themselves) |
| `policy/`, `policy-tests/` | Lab A: OPA/Rego storage policy and its unit tests |
| `k8s/` | Lab D: Kyverno admission policies and the insecure / conforming manifests |
| `infra/` | The Terraform the IaC gate scans |
| `app/` | Planted findings for the secret, SAST and dependency gates |
| `labs/` | Write-ups for all nine labs (A–I) with control mappings |

The pipeline history is part of the evidence: the first run, the red run and the green
run are kept, not squashed.
