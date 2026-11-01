# LAB E — DevSecOps: Security Gates in the Pipeline
Self-directed security lab · own GitHub repository · synthetic findings only

**This lab needs no Azure subscription.** It runs entirely on GitHub Actions,
which makes it the right one to do while billing propagates.

---

## THE IDEA IN ONE SENTENCE

Advisory scanning gets ignored. A failed build does not.

Every security tool in this pipeline is configured to **block**, not to warn.
`soft_fail: false`, `exit-code: 1`, no `continue-on-error`. That single
configuration choice is the difference between DevSecOps and a dashboard
nobody reads.

---

## WHAT THIS LAB PROVES

| Job requirement | Proven by |
|---|---|
| "Experience implementing security controls in CI/CD and DevSecOps environments" | Four blocking gates, demonstrated failing and passing |
| "Build security controls into CI/CD pipelines" | The workflow file itself |
| "Knowledge of vulnerability management" | Trivy, severity-gated at HIGH |
| "configuration management" | Checkov plus the OPA policy from Lab A |
| "policy frameworks such as OPA" | Conftest runs our own Rego in the pipeline |

## CONTROL FRAMEWORK MAPPING

| Framework | Control | Satisfied by |
|---|---|---|
| **NERC CIP-010-4** | R1 Configuration Change Management | Every change passes automated gates before merge |
| **NERC CIP-013-2** | R1 Supply Chain Risk Management | Dependency scanning on every build |
| **NERC CIP-007-6** | R2 Security Patch Management | Trivy flags known-vulnerable dependencies |
| **NIST SP 800-53** | SA-11 Developer Testing and Evaluation | SAST on every push |
| | SA-15 Development Process and Tools | The pipeline is the documented process |
| | CM-3 Configuration Change Control | Gates are the change control |
| | RA-5 Vulnerability Monitoring | Continuous, not periodic |
| | SI-2 Flaw Remediation | Build fails until fixed |
| **NIST CSF 2.0** | PR.PS-06 Secure SDLC | The whole workflow |
| | ID.RA-01 Vulnerabilities identified | Gate output |
| **OWASP** | SAMM / DevSecOps maturity | Automated verification stage |

---

## THE FIVE GATES

| Gate | Tool | Catches |
|---|---|---|
| 0 · **Policy self-test** | conftest + Kyverno CLI | **A policy that has stopped working** |
| 1 · Secret scanning | gitleaks | Credentials committed to source or history |
| 2 · Infrastructure as code | Checkov + **our own Conftest policy** | Misconfigured cloud resources before deployment |
| 3 · Static analysis | Semgrep | Insecure code patterns |
| 4 · Dependencies and image | Trivy | Known CVEs at HIGH or CRITICAL |

### Gate 0 tests the gates

Gates 1–4 are standard DevSecOps content. Gate 0 asks the question underneath all of them: **who tests the tests?**

It runs the Lab A policy unit tests, then feeds the known-bad Kubernetes
manifest from Lab D through the admission policies and **fails the build if that
workload is accepted**. It also fails if the *conforming* manifest is refused,
because a policy that denies everything is not a control, it is an outage.

The reason this matters: a policy gate that has silently stopped evaluating
fails open. Nothing turns red. The pipeline is green, the dashboard says zero
violations, and `zero violations` is indistinguishable from `zero rules ran`.
Every other gate in this file is trusted on the assumption that its rules still
work — Gate 0 is the only one that checks.

It is also fast and free: no cluster, no cloud account, no credentials. Both
tools run against files, in about a second. There is no reason not to have it.

### Repository layout Gate 0 expects

```
policy/        storage.rego                  (from lab-a/policy/)
policy-tests/  run-policy-tests.sh + *.json  (from lab-a/test/)
k8s/policies/  kyverno-baseline.yaml         (from lab-d/policies/)
k8s/manifests/ insecure- and secure-*.yaml   (from lab-d/manifests/)
infra/         main.tf                       (from lab-a/insecure/, then secure/)
app/           config.py                     (the planted finding)
```

Verified in that exact layout before handover: policy unit tests 4/4, insecure
manifest 8 denials, secure manifest 0.

Gate 2 runs **both** a public ruleset and the Rego policy written in Lab A.
That pairing is deliberate and worth explaining: Checkov is breadth — other
people's rules, good coverage, no knowledge of your environment. The OPA policy
is intent — your requirements, including ones no public ruleset knows about.
A mature pipeline has both.

---

## THE PLANTED FINDING

`app/config.py` contains a credential. It is **AWS's own published example key**
from their documentation — `AKIAIOSFODNN7EXAMPLE`. It is not a real credential
and never was. It exists so Gate 1 has something to catch.

`infra/main.tf` is the deliberately insecure storage baseline from Lab A, so
Gate 2 has something to catch.

**Never plant a real credential, not even an expired one, not even in a private
repo.** Git history is forever and the habit is what matters.

---

## RUNNING IT

### Step 1 — create the repository

```bash
gh repo create security-labs --public --description "Self-directed cloud and AI security labs"
cd security-labs
# copy lab-e contents in
git add .
git commit -m "Lab E: DevSecOps security gates with planted findings"
git push -u origin main
```

### Step 2 — watch it fail

Actions tab. Expect **Gate 1 and Gate 2 to fail.**

**EVIDENCE 1:** screenshot the failed run with the red gates, and the gitleaks
output identifying the secret by file and line.

### Step 3 — remediate

```bash
# Gate 1: remove the credential, use environment variables
git rm --cached app/config.py   # then rewrite it without the key

# Gate 2: swap to the remediated baseline
cp ../lab-a/secure/main.tf infra/main.tf

git commit -am "Remediate: remove hardcoded credential, fix storage baseline"
git push
```

### Step 4 — watch it pass

**EVIDENCE 2:** the green run.
**EVIDENCE 3:** the two runs side by side in the Actions list — red above,
green below. That is the artifact.

---

## IMPORTANT — WHAT REMOVING A SECRET ACTUALLY REQUIRES

Deleting the line in a new commit makes the gate pass, because gitleaks in this
configuration scans the working tree and recent history.

**That does not remove the secret.** It remains in git history and is
recoverable by anyone with the repository.

A real remediation is:
1. **Rotate the credential first.** Always first. The exposed secret must be
   assumed compromised from the moment it was pushed.
2. Then remove it from history (`git filter-repo` or BFG).
3. Then force-push, and have every clone re-cloned.

Secret scanning is a detective control, not a preventive one: deleting the line
is not remediation.

---

## EXTENDING INTO HARNESS

The same four gates map directly onto Harness CI stages, which is worth doing
afterwards since you already have an account — the posting names DevSecOps
workflows and Harness is a credible platform to have used.

Order: get it green in GitHub Actions first, then port. Porting a working
pipeline teaches the platform; debugging two unfamiliar things at once teaches
nothing.

