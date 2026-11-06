# LAB A — Infrastructure as Code Security: Terraform + Policy as Code
Self-directed security lab · own Azure subscription · synthetic resources only

---

## WHAT THIS LAB PROVES

| Job requirement (ISO-NE Cyber Security Analyst) | Proven by |
|---|---|
| "Familiarity with Terraform, infrastructure-as-code" | You write and plan the Terraform |
| "policy frameworks such as OPA" | You write the Rego policy that blocks the deploy |
| "configuration management" | Baseline defined in code, drift impossible |
| "vulnerability assessments and configuration reviews" | Checkov + tfsec scan output |
| "Review baseline configurations ... and compliance controls" | The standards mapping below |

## CONTROL FRAMEWORK MAPPING — the part that matters

This is not "I ran a scanner." This is a control implemented and evidenced
against named standards. Learn these mappings; they are what a CIP-regulated
employer actually asks about.

| Framework | Control | How this lab satisfies it |
|---|---|---|
| **NERC CIP-010-4** | R1 — Configuration Change Management | Baseline is declared in Terraform; every change is a reviewable diff |
| **NERC CIP-010-4** | R3 — Vulnerability Assessments | Checkov/tfsec run as an assessment before deployment |
| **NERC CIP-011-3** | R1 — Information Protection | Storage denies public access, enforces TLS |
| **NIST SP 800-53 Rev 5** | CM-2 Baseline Configuration | The .tf file *is* the baseline |
| **NIST SP 800-53 Rev 5** | CM-3 Configuration Change Control | Policy gate blocks non-conforming change |
| **NIST SP 800-53 Rev 5** | CM-6 Configuration Settings | Enforced settings, not advisory |
| **NIST SP 800-53 Rev 5** | SC-8 Transmission Confidentiality | min_tls_version enforcement |
| **NIST SP 800-53 Rev 5** | SC-28 Protection of Information at Rest | Secure transfer required |
| **NIST CSF 2.0** | PR.PS-01 Configuration management practices | The whole pipeline |
| **NIST CSF 2.0** | ID.RA-01 Vulnerabilities identified | Scanner findings |
| **ISO/IEC 27001:2022** | A.8.9 Configuration management | Declared, enforced, auditable |
| **CIS Microsoft Azure Foundations Benchmark** | Storage: public access disabled, secure transfer required, minimum TLS | Each is a named deny rule |

**Why CIP-010 R1 is the headline.** In a NERC CIP environment the hardest
recurring audit finding is proving that a configuration change was authorized,
tested and documented. Infrastructure as code answers that structurally: the
baseline is a file, the change is a pull request, the test is the policy gate,
and the evidence is the commit history.

---

## COST AND SAFETY

- **Cost:** storage accounts cost pennies. This lab should be under $1.
  Still set a budget alert first (see Lab 0).
- **Scope:** your own Azure subscription only. Never run a scanner, a policy
  or a plan against anything belonging to an employer.
- **Teardown:** `terraform destroy` when your screenshots are captured.

---

## PREREQUISITES

```bash
# macOS
brew install terraform conftest tfsec
brew install checkov        # or: pip install checkov
az login
az account show             # confirm you are in YOUR subscription
```

---

## STEP 1 — Plan the deliberately insecure baseline

`insecure/main.tf` declares a storage account with three real misconfigurations:
public blob access enabled, TLS 1.0 permitted, and HTTPS-only disabled.

```bash
cd insecure
terraform init
terraform plan -out=tfplan.binary
terraform show -json tfplan.binary > ../tfplan.json
```

**Do not apply it.** The point is that it never reaches Azure.

---

## STEP 2 — Scan it

```bash
cd ..
checkov -f insecure/main.tf --compact
tfsec insecure/
```

**EVIDENCE 1:** screenshot the scanner output showing the failed checks, with
the CKV IDs visible.

---

## STEP 3 — Block it with your own policy

The scanners are someone else's opinion. The Rego policy is yours, and writing
your own is what separates a tool user from an engineer.

```bash
conftest test tfplan.json -p policy/
```

Expected: three failures, each citing the control it violates.

**EVIDENCE 2:** screenshot the conftest output. This is the strongest single
artifact in the lab — a policy you wrote, refusing a deployment, citing CIS and
NIST control IDs.

---

## STEP 3b — Test the policy itself (already done, and it passes)

A policy gate that is wrong is worse than no gate: it fails open silently while
everyone believes a control is in place. So the policy has unit tests.

```bash
./test/run-policy-tests.sh
```

```
  Lab A — OPA policy unit tests
  -----------------------------
  PASS  insecure   3 denial(s)
  PASS  secure     0 denial(s)
  PASS  untagged   1 denial(s)
  PASS  noop       0 denial(s)

  4 passed, 0 failed
```

The fixtures in `test/` are terraform-plan JSON shaped by hand, so the policy
can be tested **with no Azure subscription, no credentials and no `terraform
init`**, in under a second. That is what makes it cheap enough to run on every
commit.

Three of the cases are obvious. The fourth is the one that matters:

**`tfplan-noop.json`** describes a storage account with every misconfiguration —
but the plan action is `no-op`, because nothing about it is changing. The policy
correctly stays silent, since it only evaluates `create` and `update`.

Without that fixture, a regression that made the policy fire on *every* plan,
including unchanged resources, would pass unnoticed until the day it blocked an
unrelated deployment and someone disabled the gate to ship. **Testing that a
control does not fire when it shouldn't is as important as testing that it
does**, and it is the half almost everyone skips.

---

## STEP 4 — Fix and re-run

`secure/main.tf` is the remediated baseline.

```bash
cd secure
terraform init
terraform plan -out=tfplan.binary
terraform show -json tfplan.binary > ../tfplan-secure.json
cd ..
conftest test tfplan-secure.json -p policy/
```

Expected: pass.

**EVIDENCE 3:** the passing run, side by side with the failing one.

---

## STEP 5 — Apply, verify, destroy

```bash
cd secure
terraform apply
az storage account show -n <name> -g <rg> \
  --query "{tls:minimumTlsVersion, https:supportsHttpsTrafficOnly, public:allowBlobPublicAccess}"
terraform destroy
```

**EVIDENCE 4:** the `az` output proving the live resource matches the baseline.

---

## WHAT TO WRITE UP

Four screenshots and roughly 150 words. The write-up says:

> I declared an Azure storage baseline in Terraform, scanned it with Checkov and
> tfsec, and wrote an OPA policy that fails the plan when public blob access is
> enabled, TLS is below 1.2, or secure transfer is off. The policy cites CIS
> Azure Benchmark and NIST 800-53 control IDs in its denial messages, so a
> failed build tells the engineer which control they broke rather than just
> that something is wrong. This is the structural answer to NERC CIP-010 R1:
> the baseline is a file, the change is a diff, the test is automated, and the
> evidence is the commit history.

Do not pad it. The screenshots carry the weight.

