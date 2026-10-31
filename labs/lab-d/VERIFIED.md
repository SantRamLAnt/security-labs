# LAB D — VERIFIED POLICY OUTPUT

The Kyverno policies in `policies/kyverno-baseline.yaml` were run against both
manifests with the Kyverno CLI (v1.13.4) before this lab was handed over, so the
policies are known to work rather than assumed to.

This is **not** a substitute for Step 1–3 of the README. Running it on a live
`kind` cluster proves the admission webhook actually refuses the deployment,
which is the screenshot that belongs in the portfolio. This file proves the
policy logic is correct, which is what makes that run worth your time.

```
kyverno apply policies/kyverno-baseline.yaml --resource manifests/insecure-deployment.yaml
```

## Insecure manifest — 8 failures, 1 pass

```
Applying 27 policy rule(s) to 1 resource(s)...

policy restricted-pod-baseline -> resource workloads/Deployment/outage-portal failed:
1 - autogen-no-privileged-containers validation error:
    [CIS Kubernetes 5.2.1] [NIST 800-53 CM-7 Least Functionality] [NERC CIP-007-6 R5]
    privileged: true is effectively root on the node.
    failed at path /spec/template/spec/containers/0/securityContext/privileged/
2 - autogen-no-privilege-escalation validation error:
    [CIS Kubernetes 5.2.5] [NIST 800-53 AC-6 Least Privilege]
    allowPrivilegeEscalation must be false.
    failed at path /spec/template/spec/containers/0/securityContext/allowPrivilegeEscalation/
3 - autogen-run-as-non-root validation error:
    [CIS Kubernetes 5.2.6] [NIST 800-53 SC-39 Process Isolation]
    Containers must run as a non-root user.
    failed at path /spec/template/spec/containers/0/securityContext/runAsNonRoot/
4 - autogen-no-host-namespaces validation error:
    [CIS Kubernetes 5.2.2-5.2.4] [NIST 800-53 SC-39] [NERC CIP-005-7 R1]
    hostNetwork, hostPID and hostIPC break container isolation.
    failed at path /spec/template/spec/hostNetwork/
5 - autogen-no-hostpath-volumes validation failure:
    [CIS Kubernetes 5.2.12] [NIST 800-53 AC-6]
    hostPath volumes mount the node filesystem into the container.
6 - autogen-drop-all-capabilities validation error:
    [CIS Kubernetes 5.2.8-5.2.9] [NIST 800-53 CM-7 Least Functionality]
    Containers must drop ALL capabilities.
    failed at path /spec/template/spec/containers/0/securityContext/capabilities/drop/

policy image-provenance -> resource workloads/Deployment/outage-portal failed:
1 - autogen-disallow-latest-tag validation error:
    [CIS Kubernetes 5.5] [NIST 800-53 CM-2 Baseline Configuration] [NERC CIP-010-4 R1]
    An unpinned or :latest tag means the running image is not necessarily the
    image that was scanned.
    failed at path /spec/template/spec/containers/0/image/

policy resource-limits-required -> resource workloads/Deployment/outage-portal failed:
1 - autogen-require-limits validation error:
    [NIST 800-53 SC-6 Resource Availability]
    A container without limits can starve every other workload on the node.
    failed at path /spec/template/spec/containers/0/resources/

pass: 1, fail: 8, warn: 0, error: 0, skip: 0
```

## Secure manifest — clean

```
Applying 27 policy rule(s) to 1 resource(s)...

pass: 9, fail: 0, warn: 0, error: 0, skip: 0
```

---

## THE DETAIL WORTH NOTICING: `autogen-`

Every rule name in that output carries an `autogen-` prefix, and the run says
**27 rules** applied when the file defines **9**.

The policies are written against `kind: Pod`. The manifest is a `Deployment`.
Kyverno auto-generated the equivalent rules for the Deployment, DaemonSet and
CronJob controllers from each Pod rule — 9 × 3 — and applied the generated ones.

This matters, and it is a good thing to be able to explain:

- **Writing policy against the Pod spec is correct**, because every workload
  controller ultimately produces pods. Writing one rule per controller kind is
  how a policy set develops gaps — someone adds a `StatefulSet` and nothing
  covers it.
- **It is also where policies silently fail.** If auto-generation is disabled,
  or a rule uses a `match` that the generator cannot translate, your Pod rule
  will never fire against a Deployment and the cluster looks compliant because
  nothing was evaluated. "Zero violations" and "zero rules ran" print the same
  in a dashboard.

So the thing to check in any admission-policy review is not whether rules exist.
It is whether they **evaluated**, and against what.

---

## REPRODUCING THIS WITHOUT A CLUSTER

```bash
brew install kyverno
cd lab-d
kyverno apply policies/kyverno-baseline.yaml --resource manifests/insecure-deployment.yaml
kyverno apply policies/kyverno-baseline.yaml --resource manifests/secure-deployment.yaml
```

No cluster, no cloud account, about a second. Which means it belongs in CI on
every change to the policy file — same argument as the Lab A policy unit tests.
