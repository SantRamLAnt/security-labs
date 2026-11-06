# LAB C — Identity: Least Privilege, Custom RBAC and Entitlement Review
Microsoft Entra ID · Azure RBAC · CIEM · Conditional Access
Self-directed security lab · own Azure tenant only

---

## THE IDEA IN ONE SENTENCE

In cloud, identity is the perimeter — and the finding is almost never "someone
broke in," it is "someone already had more access than anyone remembered
granting."

---

## WHAT THIS LAB PROVES

| Job requirement | Proven by |
|---|---|
| "identity and access management" | Custom role, scoped assignment, entitlement review |
| "Review ... access controls" | The assignment audit in Step 2 |
| "principle of least privilege" | A role built from the minimum action set, not from Contributor |
| "cloud security architecture" | Conditional Access design in Step 4 |
| "Identify and track remediation of security findings" | Over-privileged assignment found, narrowed, re-verified |

## CONTROL FRAMEWORK MAPPING

| Framework | Control | Satisfied by |
|---|---|---|
| **NERC CIP-004-7** | R4 Access Management Program | The documented entitlement review |
| | R5 Access Revocation | The removal step, timed |
| **NERC CIP-005-7** | R2 Interactive Remote Access | Conditional Access + MFA design |
| **NERC CIP-007-6** | R5 System Access Control | Least-privilege role definition |
| **NIST SP 800-53 Rev 5** | AC-2 Account Management | Inventory of principals and assignments |
| | AC-3 Access Enforcement | RBAC assignment at the narrowest scope |
| | AC-5 Separation of Duties | Reader vs operator split |
| | AC-6 Least Privilege | The custom role |
| | AC-6(7) Review of User Privileges | Step 2 audit |
| | IA-2(1) MFA to Privileged Accounts | Conditional Access |
| **NIST CSF 2.0** | PR.AA-01…05 Identity, credentials, access | The whole lab |
| **CIS Azure Foundations** | Identity and Access Management section | Step 3 checks |
| **ISO/IEC 27001:2022** | A.5.15 Access control · A.5.18 Access rights | Review and revocation |

---

## COST AND SAFETY

- **Cost: $0.** RBAC, custom roles and assignment queries are free.
- **PIM and Access Reviews need Entra ID P2.** Do not buy a license for a lab.
  Step 5 covers how to answer the PIM question honestly without having run it,
  which is better than pretending.
- **Scope: your own tenant.** Never enumerate an employer's directory. Reading
  a corporate directory without authorization is a security incident with your
  name on it, regardless of intent.

---

## STEP 1 — Inventory what exists

You cannot review access you have not listed.

```bash
az login
SUB=$(az account show --query id -o tsv)

# Every role assignment in the subscription, with the principal resolved
az role assignment list --all --include-inherited \
  --query "[].{principal:principalName, type:principalType, role:roleDefinitionName, scope:scope}" \
  -o table

# Service principals that can act without a human
az ad sp list --all --query "length(@)"

# Anything holding Owner or Contributor at subscription scope
az role assignment list --all \
  --query "[?roleDefinitionName=='Owner' || roleDefinitionName=='Contributor'].{p:principalName, r:roleDefinitionName, s:scope}" \
  -o table
```

**EVIDENCE 1:** the assignment table.

Then answer, in writing, for each row: **who granted this, when, and what
breaks if it is removed?** Most real environments cannot answer that for most
rows. That inability *is* the finding — write it up as one rather than skipping
past it.

---

## STEP 2 — Find the over-privileged assignment

In a personal subscription the finding is predictable and still worth
documenting properly: the human account holds **Owner at subscription scope**,
and any automation principal almost certainly holds **Contributor** when it
needs far less.

For each non-human principal, establish what it actually uses. Activity log is
the evidence:

```bash
az monitor activity-log list \
  --start-time $(date -u -v-30d +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -d '30 days ago' +%Y-%m-%dT%H:%M:%SZ) \
  --query "[].{caller:caller, op:operationName.value, status:status.value}" \
  -o tsv | sort | uniq -c | sort -rn | head -40
```

That list of operations is the real entitlement requirement. Everything granted
beyond it is standing privilege with no demonstrated need — which is the exact
definition CIEM tools sell against, and you can produce it with one query.

**EVIDENCE 2:** operations actually used vs permissions actually held, as a
two-column table. This is the strongest artifact in the lab.

---

## STEP 3 — Build the role from the minimum — **CREATED**

**Status, 31 Oct 2026.** `AI Security Reader` exists in `personal-ai-nonprod`:
18 Actions, **0 DataActions**, assignable only at `rg-seclab-ai`.

```
== CUSTOM ROLES ==
Role                 Actions    DataActions
-------------------  ---------  -------------
AI Security Reader   18         0

== can it retrieve a key? ==

(nothing above = the role cannot list keys)
```

The evidence is the **empty result**. A role listing that returns nothing for
`listKeys` is a stronger statement than any description of the role, because it
is a property of the definition rather than a claim about it.

### Two things that went wrong, both worth keeping

**1. Azure validates every action string.** The first create failed:

```
(InvalidActionOrNotAction) 'Microsoft.Security/regulatoryComplianceStandards/read'
does not match any of the actions supported by the providers.
```

That permission does not exist — it was plausible and wrong. **You cannot put an
invented permission in a role definition**, which is a genuinely good property:
the platform refuses to pretend a control exists. The action was removed and
the repository JSON corrected, taking the role from 20 actions to 19 (18 of
which survive in the live definition).

The wider lesson is about where validation lives. A hand-written list of
permissions is a document until something checks it. Azure checks it at create
time; nothing checks the copy sitting in a repository, which is why the file and
the live object had drifted within minutes of each other.

**2. Cloud Shell's subscription picker is not the CLI's subscription.**
Choosing `personal-ai-nonprod` when starting Cloud Shell sets where the *shell*
runs. The `az` default was still `lz-workload-nonprod`, so the first listing came
back empty — not because nothing existed, but because it was looking in the
wrong place.

An empty result read as "nothing is there" is one of the most common ways people
mis-assess an environment, and it is the same failure shape as Lab E Gate 0:
**zero findings and zero coverage look identical.** Hence `az account show`
before anything else, every time — Step 0 of Lab B, now demonstrated rather than
recommended.

---

### Building it

`rbac/ai-security-reader.role.json` defines a role that can **assess** the AI
and storage estate and **change nothing**: read resources, read diagnostic and
policy state, read Defender assessments. No data actions. No key listing.

Note what is deliberately absent: `Microsoft.CognitiveServices/accounts/listKeys/action`.
A reader who can list keys is not a reader — they are an operator with extra
steps, because the key is a bearer credential to the model endpoint. That one
omission is the whole lesson of the lab and is worth being able to explain.

```bash
SUB=$(az account show --query id -o tsv)
sed -i.bak "s|SUBSCRIPTION_ID|$SUB|g" rbac/ai-security-reader.role.json

az role definition create --role-definition rbac/ai-security-reader.role.json

# Assign at the resource group, never the subscription
az role assignment create \
  --assignee "<object-id>" \
  --role "AI Security Reader" \
  --scope "/subscriptions/$SUB/resourceGroups/rg-seclab-ai"
```

Then prove the boundary holds, which matters more than creating it:

```bash
# Should succeed
az cognitiveservices account show -n oai-seclab-lsr01 -g rg-seclab-ai

# Should fail with AuthorizationFailed — that failure is the evidence
az cognitiveservices account keys list -n oai-seclab-lsr01 -g rg-seclab-ai
```

**EVIDENCE 3:** the authorization failure. A denied action is a working control;
a screenshot of a role definition is only an intention.

---

## STEP 4 — Conditional Access: design it, then state the limit

Write the policy set you would require for privileged access:

| Policy | Target | Control | Grant |
|---|---|---|---|
| Require MFA for administrators | Directory roles: Global Admin, Privileged Role Admin, Security Admin | All cloud apps | Require MFA |
| Require MFA for Azure management | All users | Windows Azure Service Management API | Require MFA |
| Block legacy authentication | All users | All cloud apps | Block |
| Require compliant device for privileged roles | Admin roles | All cloud apps | Require compliant or hybrid-joined device |
| Sign-in risk | All users | All cloud apps | High risk → block; medium → require MFA |

Two things to say about this set, both of which are the point:

1. **Break-glass accounts are excluded from every policy above.** Two of them,
   cloud-only, long random passwords in a physical safe, monitored for any use.
   A Conditional Access policy with no exclusion is how a tenant locks its own
   administrators out, and it has happened to real organizations.
2. **The risk-based policies require Entra ID P2.** The MFA and legacy-auth
   policies do not. Knowing which controls your license actually buys is part
   of the job.

**EVIDENCE 4:** the written policy set, with exclusions named. Implement the
MFA and legacy-auth policies if your tenant allows it; do not buy P2 for a lab.

---

## STEP 5 — PIM: the honest version

Privileged Identity Management replaces standing privilege with eligible
privilege: you hold no role until you activate it, for a bounded window, with
justification, approval and an audit record.

There is no P2 license here, so it was not run. Stated plainly, with what was done instead:

> I haven't operated PIM — it needs P2 and I wasn't going to buy a license for a
> lab. What I did was the problem underneath it: I pulled every role assignment
> in my subscription, pulled thirty days of activity log to see which
> permissions were actually exercised, and wrote a custom role from that
> intersection. PIM removes standing privilege in time; least-privilege role
> design removes it in scope. You want both, and the scope work has to come
> first or you are just time-boxing an over-broad role.

That describes the control rather than the product.

