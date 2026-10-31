# LAB G — AI Threat Model
## Utility Helpdesk Assistant (RAG over operational knowledge base)

Author: Luis A. Santiago-Ramirez
Self-directed security lab · threat model of the Lab F system
Frameworks: MITRE ATLAS · OWASP Top 10 for LLM Applications 2025 · NIST AI RMF 1.0

---

## 1. SCOPE AND PURPOSE

This document threat-models a generative AI assistant of the kind a utility
would realistically deploy: a customer and field-facing helpdesk bot that
answers questions about outages, billing and service status by retrieving from
an internal knowledge base.

It is modelled as a **lab system**, not a production one. The threats and
mitigations are real; the deployment is synthetic.

The purpose is to answer the question a security reviewer actually asks, which
is not "is the model accurate" but **"what can it reach, and what can it say."**

---

## 2. SYSTEM DESCRIPTION

### 2.1 Components

| ID | Component | Trust level |
|---|---|---|
| C1 | Web chat interface | Untrusted input |
| C2 | Orchestration service (prompt assembly, tool routing) | Trusted |
| C3 | System prompt / instruction template | Trusted, but **user-reachable** |
| C4 | Retrieval index over knowledge base documents | **Semi-trusted** |
| C5 | Knowledge base source documents | **Semi-trusted** |
| C6 | Foundation model endpoint (Azure OpenAI) | Third party |
| C7 | Tool / function-calling layer (account lookup) | Trusted, privileged |
| C8 | Operational data store reached by C7 | Trusted, sensitive |
| C9 | Logging and telemetry | Trusted, sensitive |

### 2.2 Trust boundaries

- **TB1** — Browser to orchestration service. Classic untrusted input.
- **TB2** — Orchestration service to model endpoint. Data leaves the tenancy.
- **TB3** — Retrieved documents into the prompt. **The boundary most teams miss.**
- **TB4** — Model output to the tool layer. Model output is untrusted input to
  anything it can invoke.
- **TB5** — Tool layer to operational data.

### 2.3 The two assumptions that drive everything below

1. **The system prompt is reachable.** Any instruction placed in it must be
   assumed recoverable by a determined user. It is a configuration file with a
   conversational interface, not a secret store.
2. **Model output is untrusted input.** The moment output can trigger an action,
   it has the same trust level as the user who prompted it.

---

## 3. THREAT ENUMERATION

Each threat carries its MITRE ATLAS technique and OWASP LLM risk.

### T1 — Direct prompt injection
**ATLAS:** AML.T0051 LLM Prompt Injection · **OWASP:** LLM01 · **Boundary:** TB1

User instructs the model to disregard its instructions and act outside policy.

*Impact:* policy bypass, disclosure of instruction content, unauthorised tool use.
*Likelihood:* High. This requires no skill and is attempted constantly.

**Mitigations**
- Input classification before the prompt is assembled (Azure AI Content Safety
  Prompt Shields).
- Privilege separation: the model's capability ceiling is set by the tool layer,
  not by instructions in the prompt.
- Output filtering for known-sensitive patterns.

*Residual risk:* **Medium.** Input classification has bypasses, always. The
privilege ceiling is what actually bounds the damage.

---

### T2 — Indirect prompt injection via retrieved content
**ATLAS:** AML.T0051.001 · **OWASP:** LLM01 · **Boundary:** TB3

A malicious instruction is embedded in a document the system retrieves — a
customer email, a scanned work order, a vendor PDF. The user never sees it.

*Impact:* the same as T1, but **the victim is unaware and there is no malicious
user to detect.**
*Likelihood:* Medium now, rising fast as retrieval surfaces expand.

**Mitigations**
- Treat all retrieved content as untrusted data, never as instruction.
- Structural delimiting of retrieved content, with the system prompt stating
  that content inside the delimiters is data.
- Provenance checks on indexed documents; restrict who can write to the index.
- Content scanning at ingestion, not only at query time.

*Residual risk:* **High.** This is the hardest threat in the model. The
industry does not yet have a robust answer, and saying so is more honest than
claiming a control that does not exist.

---

### T3 — System prompt leakage
**ATLAS:** AML.T0056 · **OWASP:** LLM07 · **Boundary:** TB1

Extraction of instructions, tool definitions or embedded values.

*Impact:* reveals business logic, tool surface, and anything foolishly stored
in the prompt. Leakage is also reconnaissance for T1 and T6.

**Mitigations**
- **Architectural:** no secrets, credentials or access codes in the prompt. Ever.
  Retrieve them at call time behind an authorisation check.
- Refusal instructions for meta-questions about configuration.
- Canary tokens in the prompt to detect leakage in testing (see Lab F).

*Residual risk:* **Low**, once the architectural fix is applied. The prompt
leaking matters only in proportion to what was put in it.

---

### T4 — Sensitive information disclosure
**ATLAS:** AML.T0057 LLM Data Leakage · **OWASP:** LLM02 · **Boundary:** TB4, TB5

The assistant returns customer PII, operational detail, or data belonging to a
different customer.

*Impact:* privacy breach; in a utility context, potentially **CIP-011 BES Cyber
System Information** exposure.
*Likelihood:* Medium, and frequently accidental rather than attacked.

**Mitigations**
- Authorisation enforced at the data layer, scoped to the authenticated user —
  not by asking the model to be discreet.
- DLP and sensitivity labelling on the data before it reaches the index (Lab H).
- Output scanning for identifier patterns.
- Minimise what the index contains in the first place.

*Residual risk:* **Medium.** Mitigated well by authorisation, poorly by prompting.

---

### T5 — Excessive agency
**OWASP:** LLM06 · **Boundary:** TB4

The model invokes a tool with more authority than the interaction warrants —
modifying records, dispatching work, issuing credits.

*Impact:* unauthorised state change. In an operational context this is the
threat with physical consequences.

**Mitigations**
- Least privilege on every tool. Read-only by default.
- Human confirmation for any state-changing action.
- Per-tool authorisation evaluated against the end user, not the service identity.
- Rate limiting and anomaly detection on tool invocation.

*Residual risk:* **Low**, and only because the mitigation is conventional
engineering rather than anything AI-specific. This is the threat most
improved by treating the model as an untrusted client.

---

### T6 — Training data and index poisoning
**ATLAS:** AML.T0020 Poison Training Data · **OWASP:** LLM04 · **Boundary:** TB3

An adversary with write access to the knowledge base inserts content that
corrupts future answers.

*Impact:* persistent misinformation, with an operational safety dimension — an
assistant that confidently gives wrong isolation guidance is a hazard.

**Mitigations**
- Access control and change review on index sources.
- Integrity checking and provenance metadata per document.
- Periodic regression testing of answers against a known-good question set.

*Residual risk:* **Medium.** Detection is slow; a poisoned index looks normal.

---

### T7 — Model theft and extraction
**ATLAS:** AML.T0048 · **OWASP:** LLM10 (adjacent) · **Boundary:** TB2

Systematic querying to reconstruct proprietary behaviour, fine-tuning data or
the knowledge base.

*Impact:* IP loss; for a RAG system the realistic loss is **the corpus, not the
model**.
*Likelihood:* Low for a commodity hosted model; higher where the index is the
valuable asset.

**Mitigations**
- Rate limiting and per-principal quotas.
- Anomaly detection on high-volume, high-entropy query patterns.
- Authentication on the endpoint; no anonymous access.

*Residual risk:* **Low.**

---

### T8 — Unbounded consumption
**OWASP:** LLM10 · **Boundary:** TB1, TB2

Adversarial prompts that drive token or compute cost, as denial of wallet or
denial of service.

**Mitigations** — max token limits per request, per-user quotas, cost alerting
on the model endpoint, request timeouts.

*Residual risk:* **Low.** Cost controls are unglamorous and effective.

---

### T9 — Misinformation and overreliance
**OWASP:** LLM09 · **Boundary:** TB4

A fluent, confident, wrong answer — particularly dangerous where the question
touches physical safety.

*Impact:* **this is the threat with the clearest path to someone getting hurt.**
An assistant that answers "can I repair this gas line myself" wrongly is not a
quality problem.

**Mitigations**
- Hard topic exclusions for safety-critical guidance, enforced outside the model.
- Citation of retrieved sources so answers are checkable.
- Explicit escalation paths to a human.
- Visible interface disclosure that responses are machine-generated.

*Residual risk:* **Medium.** Partly a design and interface problem, not purely
a security one — which is itself worth stating in a threat model.

---

### T10 — Supply chain of the model and its dependencies
**OWASP:** LLM03 · **Boundary:** TB2

Compromise or unexpected change in the hosted model, SDK or plugin layer.
Model version changes can silently alter safety behaviour.

**Mitigations** — pin model versions, regression-test on version change,
vendor security review, SBOM for the application layer.

*Residual risk:* **Medium.** Largely inherited from the provider, which is the
honest characterisation.

---

## 4. RISK SUMMARY

| ID | Threat | OWASP | ATLAS | Likelihood | Impact | Residual |
|---|---|---|---|---|---|---|
| T1 | Direct prompt injection | LLM01 | AML.T0051 | High | Medium | Medium |
| T2 | Indirect injection via retrieval | LLM01 | AML.T0051.001 | Medium | High | **High** |
| T3 | System prompt leakage | LLM07 | AML.T0056 | High | Low | Low |
| T4 | Sensitive information disclosure | LLM02 | AML.T0057 | Medium | High | Medium |
| T5 | Excessive agency | LLM06 | — | Low | High | Low |
| T6 | Index / data poisoning | LLM04 | AML.T0020 | Low | High | Medium |
| T7 | Model / corpus extraction | — | AML.T0048 | Low | Medium | Low |
| T8 | Unbounded consumption | LLM10 | — | Medium | Low | Low |
| T9 | Misinformation / overreliance | LLM09 | — | Medium | **High** | Medium |
| T10 | Supply chain | LLM03 | — | Low | High | Medium |

**Highest residual risk: T2, indirect prompt injection.** Stated plainly
because a threat model that claims everything is mitigated is not a threat
model, it is marketing.

---

## 5. NIST AI RMF ALIGNMENT

| Function | Category | Evidence |
|---|---|---|
| GOVERN 1.2 | Risk management integrated into AI lifecycle | This document, maintained alongside the system |
| MAP 5.1 | Likelihood and impact of impacts characterised | Section 4 |
| MEASURE 2.7 | Security and resilience evaluated | Lab F test suite and results |
| MANAGE 2.2 | Mechanisms sustain AI risk management | Guardrails, quotas, regression tests |
| MANAGE 4.1 | Post-deployment monitoring planned | Telemetry on refusals, tool calls and cost |

---

## 6. WHY THIS MATTERS AT A GRID OPERATOR

The threats above are generic to GenAI. What changes in a utility or system
operator context is the impact column.

**T4 becomes an information protection obligation.** The moment an assistant can
reach operational data, disclosure stops being a privacy inconvenience and
starts being NERC CIP-011 BES Cyber System Information.

**T9 becomes a safety issue.** Confidently wrong guidance about isolating a main
or approaching equipment has a physical consequence that no amount of model
evaluation metrics captures.

**T5 becomes the one that keeps you up.** An assistant with a write-capable tool
in an operational environment is an unauthenticated path to a state change.
Read-only by default is not conservatism, it is the control.

That reframing is the thing seven years inside utility operations contributes to
an AI security review, and it is not available from a certification.

---

## 7. REVIEW

This model is a point-in-time assessment of a lab system. It should be revisited
on any change to the tool surface, the retrieval corpus, the model version, or
the authentication model — those four changes being the ones that move the risk
table.
