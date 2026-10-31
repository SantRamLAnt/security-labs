# LAB I — Detection Engineering in Microsoft Sentinel
KQL analytics rules · MITRE ATT&CK mapping · incident triage
Self-directed security lab · own subscription · synthetic and own-activity data only

---

## THE IDEA IN ONE SENTENCE

Every other lab in this portfolio **prevents** something. This one assumes the
prevention failed and asks the only question left: *would anyone have known?*

The five detections here are deliberately not generic SIEM content. Each one
detects the bypass of a control built earlier in this portfolio:

| Detection | Detects the bypass of |
|---|---|
| Policy assignment deleted or disabled | Lab B |
| Cognitive Services key listed | Lab C (the one action the custom role denies) |
| Anomalous model endpoint volume | Lab F (T8 unbounded consumption) |
| Role assignment elevated at subscription scope | Lab C |
| Legacy authentication sign-in | Lab C Conditional Access |

A detection set that mirrors your own control set is a coherent security
programme in miniature, and that coherence is the thing worth presenting.

---

## WHAT THIS LAB PROVES

| Job requirement | Proven by |
|---|---|
| "Experience with SIEM" | A working workspace with rules you wrote |
| "Monitor and analyse security events" | The hunting queries and triage notes |
| "Threat detection" / "incident response" | Rules, incidents, and a documented triage |
| "Knowledge of MITRE ATT&CK" | Every rule carries tactic and technique |
| "Identify and track remediation of security findings" | The incident workflow in Step 4 |

## CONTROL FRAMEWORK MAPPING

| Framework | Control | Satisfied by |
|---|---|---|
| **NERC CIP-007-6** | R4 Security Event Monitoring — log events, alert on them, review | The whole lab; R4 is the single closest CIP requirement to a SIEM |
| **NERC CIP-008-6** | R1 Incident Response Plan · R2 Implementation and testing | Triage workflow, Step 4 |
| **NERC CIP-015-1** | Internal Network Security Monitoring | The direction this is all moving; worth naming |
| **NIST SP 800-53 Rev 5** | AU-2 Event Logging · AU-6 Audit Review and Analysis | Connectors and rules |
| | SI-4 System Monitoring | Analytics rules |
| | IR-4 Incident Handling · IR-5 Incident Monitoring | Incident workflow |
| **NIST CSF 2.0** | DE.CM-01/09 Monitoring · DE.AE-02/03 Event analysis · RS.AN-03 Analysis | Rules and triage |
| **MITRE ATT&CK** | Per rule, below | Rule metadata |

---

## COST — READ THIS BEFORE ENABLING ANYTHING

Sentinel bills on **data ingested**, and the bill is driven by which connectors
you turn on, not by the rules you write.

- Connect **Azure Activity** only. It is low-volume and it carries every event
  these five detections need.
- **Do not** connect Entra ID sign-in logs, Defender, Office, or any
  network/syslog connector in a lab. Those are the expensive ones.
- Microsoft offers a free trial allowance on new workspaces and has changed its
  terms more than once. **Check the current terms on the Sentinel pricing page
  before you enable it, and re-check the budget alert.** Do not take a figure
  from any document, including this one.
- **Set a daily ingestion cap on the workspace.** Log Analytics → Usage and
  estimated costs → Daily cap. A cap is the control; a budget alert only tells
  you afterwards.
- **Delete the resource group when the screenshots are captured.** Everything
  in this lab is disposable and should carry the `teardown` tag from Lab B.

```bash
az group create -n rg-seclab-siem -l eastus --tags teardown=true lab=lab-i
az monitor log-analytics workspace create \
  -g rg-seclab-siem -n law-seclab --retention-time 30
# Then: portal → Microsoft Sentinel → add to this workspace
# Then: Content hub → Azure Activity → connect
# Then: Log Analytics → Usage and estimated costs → Daily cap → set it
```

---

## STEP 1 — Generate the telemetry yourself

Detections need events. Produce them deliberately, in your own subscription, and
keep a timestamped note of each action — that note is your ground truth when you
check whether the rule fired.

```bash
# 1 — list a Cognitive Services key  (should alert: detect-cognitive-key-listed)
az cognitiveservices account keys list -n oai-seclab-lsr01 -g rg-seclab-ai

# 2 — delete a policy assignment     (should alert: detect-policy-assignment-removed)
az policy assignment delete --name teardown-tag-audit --scope "/subscriptions/$(az account show --query id -o tsv)"

# 3 — create then remove a role assignment at subscription scope
#     (should alert: detect-privileged-role-assignment)

# 4 — run the Lab F suite twice back to back
#     (should alert: detect-openai-volume-anomaly)
```

Activity log ingestion into the workspace typically lags several minutes. Do not
conclude a rule is broken in the first five minutes.

**EVIDENCE 1:** your action log — what you did, at what time, which rule you
expect to fire.

---

## STEP 2 — The detections

Each file in `rules/` carries the query, the ATT&CK mapping, the scheduling, and
— the part most people skip — **the expected false positives and what to do
about them.**

| Rule | ATT&CK tactic | Technique | Severity |
|---|---|---|---|
| `detect-cognitive-key-listed.kql` | Credential Access | T1552.005 Cloud Instance Metadata / credentials from cloud services | Medium |
| `detect-policy-assignment-removed.kql` | Defense Evasion | T1562.001 Impair Defenses: Disable or Modify Tools | High |
| `detect-privileged-role-assignment.kql` | Privilege Escalation / Persistence | T1098.003 Account Manipulation: Additional Cloud Roles | High |
| `detect-openai-volume-anomaly.kql` | Impact | T1496 Resource Hijacking | Medium |
| `detect-legacy-auth-signin.kql` | Initial Access | T1078.004 Valid Accounts: Cloud Accounts | Medium |

Create each in Sentinel → Analytics → Scheduled query rule. Paste the query, set
the entity mappings noted in the file, set the ATT&CK tactic, save.

**EVIDENCE 2:** the analytics rules list, enabled, with ATT&CK coverage shown on
the MITRE blade.

---

## STEP 3 — Tune one rule, and document why

Run `detect-cognitive-key-listed` over your own history. It will fire on your
own legitimate key retrieval, because you did that in Lab F.

**Do not suppress it by removing your account.** That is how detections become
decorative. Tune it properly, and write down which you chose and why:

- **Narrow the condition** — alert only when the caller is not the resource
  owner, or when the call comes from outside expected hours.
- **Lower the severity and keep it as context** — a key listing is not an
  incident on its own, but it is a strong corroborating signal alongside
  anything else.
- **Leave it noisy and accept the cost** — defensible for a small, genuinely
  rare action.

**EVIDENCE 3:** the before and after query, with the tuning rationale in two
sentences. A tuning decision with a stated reason is worth more in an interview
than ten untuned rules.

---

## STEP 4 — Triage one incident properly

Take the incident the key-listing rule raised and work it as a real one:

1. **Triage** — what fired, when, which principal, from where.
2. **Scope** — what else did that principal do in the surrounding window? One
   KQL query, pivoted on caller, not a guess.
3. **Determine** — true positive, benign true positive, or false positive. Say
   which and why. "Benign true positive" is the honest verdict here and using
   the term correctly signals real SOC exposure.
4. **Respond** — if it were malicious: rotate the key, revoke the principal's
   sessions, check for resources created, preserve the activity log.
5. **Close** with a classification and a one-paragraph note.

**EVIDENCE 4:** the closed incident with your written determination. **This is
the single most valuable artifact in the lab** — anyone can write a rule; being
able to show a worked triage is what a SOC manager is actually hiring for.

---

## STEP 5 — Tear down

```bash
az group delete -n rg-seclab-siem --yes --no-wait
```

Confirm in Cost analysis the next day that ingestion has stopped.

---

## THE WRITE-UP

> I stood up Microsoft Sentinel on my own subscription and wrote five scheduled
> analytics rules in KQL, each mapped to a MITRE ATT&CK technique and each
> detecting the bypass of a preventive control I had built earlier — policy
> assignments being removed, model endpoint keys being listed, privileged role
> assignments at subscription scope, anomalous model consumption, and legacy
> authentication. I generated the telemetry myself, tuned one rule against a
> benign true positive rather than suppressing it, and worked one incident
> through triage, scoping and closure. The workspace ran with a daily ingestion
> cap and was torn down after evidence capture.

---

## INTERVIEW ANSWERS THIS LAB EARNS YOU

**"How do you decide what to detect?"**
Work backwards from the controls. For each preventive control, ask what its
bypass looks like in telemetry — that is the detection. It produces a set that
covers your actual risk rather than whatever the vendor's content pack happens
to include, and every rule has an owner and a reason, which matters when someone
asks a year later why it exists.

**"Your rule is noisy. What do you do?"**
Find out whether the activity is rare and important, or common and uninteresting.
If it is rare and important, the noise is a logging-hygiene problem, not a rule
problem. If it is common, either narrow the condition on a real discriminator or
demote it to context that corroborates other signals. What I do not do is
exclude the account that generates the noise, because that is the account an
attacker would use.

**"What does CIP-007 R4 actually require?"**
Log security events, alert on a defined subset, and review. The requirement is
modest; what auditors actually test is whether the alerts went somewhere a human
looked and whether you can show the review happened. Which is why the artifact I
care about from this lab is the closed incident, not the rule list.

**"Why does a grid operator need this differently?"**
Because the consequence tail is physical, so the detections that matter most are
the quiet ones — a configuration drifting, a policy disappearing, a service
principal gaining a role at 3am. Loud attacks get noticed anyway. CIP-015 moving
toward internal network security monitoring is the regulator saying the same
thing: watch inside the perimeter, not just at it.

---

## RESULT — 31 Oct 2026 (what actually happened, not what was planned)

- Deployed with `deploy.sh`: workspace `law-seclab`, daily cap 0.1 GB, Sentinel enabled, Azure Activity
  connector only, three AzureActivity rules. Telemetry generated twice (17:22Z and 17:32Z).
- **Fired:** `detect-privileged-role-assignment` raised incident 1 at 17:37Z. Triaged with `triage.sh`,
  closed as **BenignPositive** with the determination written into the incident.
- **Did not fire:** the key-listing and policy-deletion rules. Their events are in the subscription
  activity log (`evidence/screens/lab-i-activitylog-source.png`) but had not reached the workspace 28
  minutes later, while role-assignment events from the same runs had
  (`evidence/screens/lab-i-workspace-ops.png`). Those two rules are therefore **untested, not passing**.
- Not done: tuning a rule against a benign true positive; the MITRE coverage blade screenshot.
- Torn down with `teardown.sh` at ~17:52Z: activity-log export removed, `rg-seclab-siem` deleted.
