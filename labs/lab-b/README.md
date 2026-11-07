# LAB B — Cloud Security Posture Management
Defender for Cloud · Azure Policy · Secure Score · regulatory compliance
Self-directed security lab · own Azure subscription only

---

## THE IDEA IN ONE SENTENCE

Lab A stopped bad infrastructure *before* it deployed. This lab is the other
half: finding what is already running and wrong.

Both are necessary and they fail differently. A pipeline gate only sees changes
that go through the pipeline. Posture management sees everything, including the
resource someone created by hand in the portal at 4pm on a Friday — which, in
every organization, is where the findings actually come from.

---

## WHAT THIS LAB PROVES

| Job requirement | Proven by |
|---|---|
| "Perform vulnerability assessments and configuration reviews of cloud environments" | Secure Score and recommendation triage across a live subscription |
| "Review baseline configurations, access controls and compliance controls" | Regulatory compliance dashboard mapped to NIST 800-53 and CIS |
| "Experience with cloud security posture management (CSPM)" | The whole lab |
| "policy frameworks" | A custom Azure Policy definition written here, not downloaded |
| "Identify and track remediation of security findings" | Before/after Secure Score with a named remediation |

## CONTROL FRAMEWORK MAPPING

| Framework | Control | Satisfied by |
|---|---|---|
| **NERC CIP-010-4** | R1 Configuration Change Management | Policy compliance state is continuous evidence of baseline conformance |
| | R3 Vulnerability Assessments | Defender assessments run continuously rather than annually |
| **NERC CIP-005-7** | R1 Electronic Security Perimeter | The public-network-access policy below is the cloud analogue |
| **NERC CIP-011-3** | R1 Information Protection | Storage and AI endpoint exposure findings |
| **NIST SP 800-53 Rev 5** | CA-7 Continuous Monitoring | Defender for Cloud itself |
| | CM-6 Configuration Settings | Azure Policy enforcement |
| | CM-8 System Component Inventory | The `teardown` tag policy |
| | RA-5 Vulnerability Monitoring and Scanning | Recommendations and assessments |
| | SC-7 Boundary Protection | Public network access denial |
| **NIST CSF 2.0** | ID.AM-01/02 Asset inventory | Inventory blade |
| | ID.IM-01 Improvements from evaluations | Secure Score movement |
| | PR.PS-01 Configuration management | Policy assignment |
| **CIS Microsoft Azure Foundations Benchmark** | Multiple | The built-in CIS initiative in the compliance dashboard |
| **ISO/IEC 27001:2022** | A.8.9 Configuration management · A.5.23 Cloud services security | Compliance dashboard |

---

## COST AND SAFETY

- **Free tier does the work here.** Foundational CSPM — Secure Score,
  recommendations, the built-in compliance standards and Azure Policy — is
  included with the subscription. **Defender CSPM** and the per-resource
  Defender plans are paid and are *not* required for this lab. Leave them off.
- If you turn a Defender plan on to see what it does, **turn it back off the
  same day** and confirm the budget alert is in place first.
- **Scope: your own subscription only.** Never point an assessment at an
  employer tenant. Reading someone else's posture without written authorization
  is not research.

---

## STEP 0 — Confirm the guardrail before anything else

```bash
az login
az account show --query "{name:name, id:id}" -o table      # must be personal-ai-nonprod
az consumption budget list --query "[].{name:name, amount:amount}" -o table
```

You already have **SmallBudget ($20/mo)** and **LLMBudget ($25/mo)**. Confirm,
don't assume.

---

## STEP 1 — Baseline the posture

Defender for Cloud → **Overview**.

Record three numbers before you change anything:

| | Value | Date |
|---|---|---|
| Secure Score | | |
| Assessed resources | | |
| Active recommendations | | |

**EVIDENCE 1:** the Overview blade, dated.

> **Note on timing.** Immediately after creating resources this page shows
> `0 assessed resources` and `Secure Score N/A`. Assessment is asynchronous and
> can lag by hours. That lag is itself worth understanding — a posture tool
> tells you about *yesterday's* configuration, which is precisely why a
> deployment-time gate (Lab A) is not optional.

---

## STEP 2 — Read the compliance dashboard properly

Defender for Cloud → **Regulatory compliance**. Add **NIST SP 800-53 Rev 5**
and **CIS Microsoft Azure Foundations Benchmark** as standards if they are not
already shown.

Do not screenshot the percentage and move on. Pick **one failing control**,
open it, and write down:

1. The control ID and its text.
2. Which resource fails it.
3. What the assessment is actually checking — the mechanical test, not the
   marketing sentence.
4. Whether the control is *automated* or *manual*. Manual controls show as
   unassessed forever and inflate or deflate the percentage; knowing this is
   the difference between reading a dashboard and believing one.

**EVIDENCE 2:** the compliance view plus your one-control write-up.

---

## STEP 3 — Write a policy the built-ins do not have — **DEPLOYED**

**Status, 31 Oct 2026.** The first of these two is no longer a file — it is a
live custom policy definition and an active assignment in the subscription.

| | |
|---|---|
| Definition | `Deny public network access on Cognitive Services accounts` |
| Type / Mode | Custom / Indexed |
| Definition location | `personal-ai-nonprod` |
| Available effects | **Audit** |
| Assignment | `seclab-cognitive-public-access-AUDIT` |
| Assignment scope | subscription `personal-ai-nonprod` |
| Enforcement | Default (enforcement on) |

Note the assignment name ends in `-AUDIT`. That is deliberate: an assignment's
effect is invisible in most list views, and naming the effect into the
assignment means nobody has to open it to know whether it blocks. Cheap habit,
saves an incident.

**First compliance evaluation takes up to about 30 minutes**, so an empty
compliance view immediately after assignment is normal and not a failure. Check
back, or force it with `az policy state trigger-scan`.

### A gotcha that will break your automation

The portal's **"Assignment name"** field does not set the assignment's `name`.
It sets `displayName`, and `name` is auto-generated:

```
Name                      Display
------------------------  ------------------------------------
e3b44ea436cf56f29e208837  seclab-cognitive-public-access-AUDIT
```

So this returns nothing at all:

```bash
az policy assignment list --query "[?contains(name,'seclab')]"   # empty
az policy assignment list --query "[?contains(displayName,'seclab')]"  # correct
```

Anything that inventories assignments by `name` silently misses every
portal-created one — and silently is the problem. A compliance script that
reports "no seclab assignments found" reads exactly like "the control is
missing", when in fact the control is there and the query is wrong.

Assignments created with `az policy assignment create --name` set both. The
mismatch only appears in a mixed portal-and-CLI estate, which is every real
estate.

---

### The two definitions

Two custom definitions are in `policy/`. Both target things that are true of
*this* subscription, which is the point — a custom policy exists because your
environment has a requirement no public ruleset knows about.

### `policy/deny-cognitive-public-network.json`

Denies creation of a Cognitive Services / Azure OpenAI account with
`publicNetworkAccess` enabled.

This one is personal: `oai-seclab-lsr01`, the AI resource deployed in Lab F,
**is reachable over the public internet and protected only by an API key.**
That is acceptable for a lab and unacceptable for anything touching operational
data. The honest framing is not "I secured my AI endpoint" — it is:

> I deployed a model endpoint the quick way, then wrote the policy that would
> have stopped me. In a CIP environment that endpoint belongs behind a private
> endpoint inside the Electronic Security Perimeter, because an API key is a
> bearer token and a bearer token is not a perimeter.

### `policy/audit-missing-teardown-tag.json`

Audits any resource lacking a `teardown` tag. This is the same rule as the
fourth Rego deny in Lab A, implemented at the platform layer instead of the
pipeline layer — deliberately, so you can talk about where a control *should*
live. Pipeline gates catch what goes through the pipeline. Azure Policy catches
the portal.

### Deploy them

```bash
SUB=$(az account show --query id -o tsv)

az policy definition create \
  --name deny-cognitive-public-network \
  --display-name "Deny public network access on Cognitive Services accounts" \
  --mode Indexed \
  --rules policy/deny-cognitive-public-network.rules.json \
  --params policy/deny-cognitive-public-network.params.json

az policy definition create \
  --name audit-missing-teardown-tag \
  --display-name "Audit resources missing a teardown tag" \
  --mode Indexed \
  --rules policy/audit-missing-teardown-tag.rules.json

# Assign in Audit mode first. Always.
az policy assignment create \
  --name teardown-tag-audit \
  --policy audit-missing-teardown-tag \
  --scope "/subscriptions/$SUB"
```

**Assign in Audit before you assign in Deny. Every time.** A Deny policy
assigned at subscription scope without a compliance pass first is how you
discover, in production, which deployment pipelines you just broke.

### Check compliance

```bash
az policy state summarize --query "value[0].results" -o json
az policy state list \
  --filter "complianceState eq 'NonCompliant'" \
  --query "value[].{res:resourceId, policy:policyDefinitionName}" -o table
```

**EVIDENCE 3:** the non-compliant list, showing your own resources named by
your own policy.

---

## STEP 4 — Remediate one thing and show the delta

Pick the single highest-impact recommendation, fix it, and wait for reassessment.

Good candidates in a subscription like this one: secure transfer required on
storage, minimum TLS version, MFA on the account, diagnostic settings absent.

**EVIDENCE 4:** Secure Score before and after, with the remediation named.

A one-point move is fine. The artifact is not the score, it is the
**before → action → after** chain, which is what remediation tracking means.

---

## STEP 5 — Tear down what you no longer need

```bash
az policy assignment delete --name teardown-tag-audit --scope "/subscriptions/$SUB"
```

Leave the definitions; they cost nothing. Delete assignments and any paid
Defender plan you enabled.


---

## RESULT — 1 Nov 2026

- Custom policy `seclab-cognitive-public-access-AUDIT` (Audit): 2 of 2 Cognitive Services accounts NonCompliant,
  `oai-seclab-lsr01` and `lasr-pai-nonprod-resource` (an older Foundry resource outside this lab).
- Defender for Cloud's first assessment, about a day after registering `Microsoft.Security`: 36 checks — 10 Healthy,
  7 NotApplicable, 19 Unhealthy. Its built-in "Microsoft Foundry resources should restrict network access" flagged the
  same 2 accounts. It also flagged key-based access on both (`evidence/screens/lab-b-defender-first-assessment.png`).
- Secure Score: **6 of 13 (46%)** on 1 Nov 2026 (`evidence/screens/lab-b-securescore-6of13.png`). This is the
  before figure. No after figure: remediation is left open by choice, so there is no delta.
- Correction. An earlier note here said the score was still null. That was my query, not Defender: I asked for
  `score.current`, but this CLI version returns the field as top-level `current`, so JMESPath printed null while the
  raw JSON held the number. The "empty is not zero" finding stands; this time the empty value came from my own query.
