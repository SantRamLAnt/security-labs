# LAB H — Data Security Posture: Classification, Labelling and DLP
Microsoft Purview · sensitivity labels · DLP · CIP-011 information protection
Self-directed security lab · synthetic data only

---

## THE IDEA IN ONE SENTENCE

Every other lab protects a *system*. This one protects the *data*, which is the
only reason the systems matter — and in a NERC CIP environment it is the
obligation with a name: CIP-011, Information Protection.

---

## WHY THIS LAB IS DIFFERENT, AND SAY SO

Labs A through G produce a screenshot of a control working. This one produces a
**classification scheme and a policy design**, because that is honestly what
data security posture management is. The tooling is the easy half; deciding
what data exists, who may see it, and what happens when it moves is the half
that takes judgement — and it is the half seven years inside a utility actually
qualifies you for.

Do not inflate this into "I deployed enterprise DLP." Say: *I built the
classification scheme and the policy design, and implemented what a personal
tenant allows.* That is a stronger sentence than a claim that will not survive
a follow-up question.

---

## WHAT THIS LAB PROVES

| Job requirement | Proven by |
|---|---|
| "Implement AI governance controls to prevent sensitive data exposure" | The AI-specific rules in Section 4 |
| "data protection" / "information protection" | The classification matrix |
| "Knowledge of regulatory requirements" | CIP-011 mapping, done properly |
| "cloud security architecture" | Where the control sits, and why not in the model |

## CONTROL FRAMEWORK MAPPING

| Framework | Control | Satisfied by |
|---|---|---|
| **NERC CIP-011-3** | R1 Information Protection Program — identify, classify, protect BCSI | Sections 2 and 3 |
| | R2 BCSI Reuse and Disposal | Retention and disposal row of the matrix |
| **NERC CIP-004-7** | R4 Access Management for BCSI | Access column of the matrix |
| **NIST SP 800-53 Rev 5** | RA-2 Security Categorization | The classification scheme itself |
| | MP-4 Media Storage · MP-6 Media Sanitization | Retention and disposal |
| | SC-28 Protection of Information at Rest | Encryption and labelling |
| | AC-4 Information Flow Enforcement | DLP egress rules |
| | SI-12 Information Management and Retention | Retention |
| **NIST CSF 2.0** | ID.AM-07 Data inventory · PR.DS-01/02 Data protected | Sections 2–4 |
| **ISO/IEC 27001:2022** | A.5.12 Classification of information · A.5.13 Labelling · A.8.12 Data leakage prevention | The whole lab |
| **OWASP LLM 2025** | LLM02 Sensitive Information Disclosure | Section 4 |

---

## SECTION 1 — Cost and scope

- Sensitivity labels and basic DLP need a Microsoft 365 / Purview licence that a
  personal tenant usually does not have. **Do not buy one for a lab.**
- What you *can* do free: build the classification scheme, write the policy
  design, and implement the storage-side controls in Azure (encryption,
  private endpoints, access scoping) that enforce the same intent.
- **Synthetic data only.** No Eversource data, no customer records, no exports
  from a work system — not into a personal tenant, not into a personal mailbox,
  not into any AI service. This is not caution, it is the rule that makes the
  rest of the portfolio defensible.

---

## SECTION 2 — The classification scheme

Four levels. Four is the number that gets used; six gets ignored.

| Level | Definition | Examples in a utility | Storage | Sharing | Retention |
|---|---|---|---|---|---|
| **Public** | Released, or releasable, without harm | Outage map, rate schedules, published maps | Any | Unrestricted | Per records schedule |
| **Internal** | Routine business; harm from disclosure is low | Work schedules, internal procedures, training material | Managed tenant | Internal only | 3 years default |
| **Confidential** | Harm to customers or the business | Customer PII, premise and account records, vendor contracts | Encrypted, access-scoped | Named recipients; no external forwarding | Per regulation; disposal recorded |
| **Restricted / BCSI** | Information about BES Cyber Systems whose exposure could enable a compromise | Network diagrams, asset inventories with addresses, system configurations, credentials, **GIS data joining asset location to criticality** | Encrypted, private network path, logged access | Need-to-know; authorised list; no third-party AI processing | CIP-011 R2 disposal evidence required |

### The row that matters, and the one you can speak to better than most candidates

**GIS data is where Confidential becomes Restricted, and it happens by join.**

A gas main centreline alone is Internal. A pressure system identifier alone is
Internal. Joined, with regulator stations, criticality and address-level
precision, the result describes how to cause harm — and that is the BCSI test:
not what the attribute is called, but what the combination enables.

This is the aggregation problem, it is poorly handled in most organisations
because classification is applied per-field, and it is a point almost no
security candidate can make from direct experience. **Lead with it.**

---

## SECTION 3 — The label and policy design

| # | Policy | Condition | Action | Control |
|---|---|---|---|---|
| 1 | Default labelling | Any unlabelled document in a managed workspace | Apply `Internal` | ISO 27001 A.5.13 |
| 2 | Automatic classification | Content matches account-number, SSN or address-plus-meter patterns | Recommend `Confidential` | NIST RA-2 |
| 3 | External egress block | `Confidential` or `Restricted` sent outside the tenant | Block, with override + business justification for `Confidential`; hard block for `Restricted` | NIST AC-4, CIP-011 R1 |
| 4 | Removable media | `Restricted` copied to USB or personal cloud storage | Block, alert security | NIST MP-4 |
| 5 | **AI service egress** | Any labelled content pasted into or uploaded to a non-approved generative AI endpoint | Block `Confidential` and `Restricted`; warn on `Internal` | OWASP LLM02, NIST AC-4 |
| 6 | Disposal | `Restricted` past retention | Documented destruction with evidence | CIP-011 R2 |

**Policy 5 is the one to talk about.** It is the control that did not need to
exist three years ago, it is the one every organisation is currently improvising,
and it is where this lab meets Lab F. The failure mode is not a hacker — it is a
competent employee pasting an operational document into a chat window to get
help faster. The control has to live at the egress boundary, because by the time
the content reaches the model it is already disclosed.

**EVIDENCE 1:** this table, as your own document.

---

## SECTION 4 — Apply it to the AI system from Labs F and G

A RAG assistant inherits the classification of whatever it indexes, and a
retrieval index is an aggregation engine — which means it can manufacture
Restricted material out of Internal documents by doing exactly what it was
built to do.

Four rules follow, and they are architectural, not prompt-level:

1. **Classify before indexing, never after.** A label applied after ingestion
   protects nothing; the content is already in the vector store.
2. **Index only at or below the lowest clearance of any user of that index.** A
   single index serving mixed audiences will leak, and no amount of prompt
   instruction fixes it. One index per audience is the control.
3. **Authorise retrieval at the data layer, per requesting user** — not by
   asking the model to withhold. Lab G T4 says the same thing from the threat
   side; this is the data side of one control.
4. **No Restricted/BCSI content reaches a third-party model endpoint.** For this
   lab's own system, `oai-seclab-lsr01` is a public-internet endpoint protected
   by an API key, which by rule 4 means **it may only ever see synthetic data** —
   which is exactly how Lab F is built.

**EVIDENCE 2:** these four rules written against the Lab G component diagram,
with the data classification of each component marked on it.

---

## SECTION 5 — What you can actually implement free

```bash
# Encryption at rest and in transit, access scoped — the Azure-side enforcement
az storage account update -n <acct> -g rg-seclab-ai \
  --min-tls-version TLS1_2 --allow-blob-public-access false

az storage account show -n <acct> -g rg-seclab-ai \
  --query "{tls:minimumTlsVersion, public:allowBlobPublicAccess, encryption:encryption.services.blob.enabled}"

# Who can read the data, at what scope
az role assignment list --scope "/subscriptions/<sub>/resourceGroups/rg-seclab-ai" -o table
```

If your tenant exposes the Purview compliance portal, create the four labels
from Section 2 and apply them to synthetic documents. If it does not, say so —
the design is the deliverable.

**EVIDENCE 3:** the enforced storage settings, or the labels if available.

---

## INTERVIEW ANSWERS THIS LAB EARNS YOU

**"How would you classify data in an environment you don't know yet?"**
Not by walking the file shares. By asking what would happen if a given dataset
appeared in public — then working backwards to the fields and, more importantly,
the *joins* that produce that outcome. Aggregation is where classification
schemes fail: every field is Internal and the combination is Restricted.

**"What's CIP-011 in practice?"**
Identify BCSI, protect it in storage, transit and use, and prove disposal. The
hard part is the identification, because BCSI is defined by what the information
*enables* rather than by where it lives. A network diagram in a PowerPoint is
still BCSI.

**"How do you stop staff pasting sensitive data into AI tools?"**
You make the approved path faster than the unapproved one, and you enforce at
egress. Blocking alone produces workarounds on personal devices, which is worse
because you lose visibility too. So: a sanctioned endpoint inside the tenant,
classification-aware DLP on the unsanctioned ones, and clear guidance on what
may go where. The control is organisational; the enforcement is technical.

**"Why does your own AI lab only use synthetic data?"**
Because it is a public endpoint authenticated by a bearer key, and my own
classification rules say Restricted material does not reach one. Applying my own
scheme to my own lab is the test of whether the scheme is real.
