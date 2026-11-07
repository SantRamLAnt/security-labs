# LAB D — Container and Kubernetes Security
Kyverno admission policy · Pod Security Standards · Trivy image scanning
Self-directed security lab · **runs locally, costs $0**

---

## WHY THIS RUNS ON YOUR LAPTOP AND NOT ON AKS

An AKS cluster costs real money per hour and you would learn nothing extra from
it. Every control in this lab — admission policy, pod security standards, image
scanning, the deny decision itself — is identical on a local `kind` cluster.

Being able to explain *that* choice is itself the senior answer. The thing being
tested is the admission controller, not Azure's bill.

If you later want the AKS line on the board: create a one-node cluster, apply
the same manifests, screenshot, `az aks delete`. Under an hour, a few dollars.
Do it last, after everything works locally.

---

## WHAT THIS LAB PROVES

| Job requirement | Proven by |
|---|---|
| "container security" | Admission policy blocking non-conforming workloads |
| "Experience with ... Kubernetes" | A working cluster with policies you wrote |
| "policy frameworks such as OPA" | Kyverno policies, plus the Gatekeeper/OPA comparison below |
| "vulnerability management" | Trivy image scan with a severity gate |
| "Review baseline configurations" | Pod Security Standards as the declared baseline |

## CONTROL FRAMEWORK MAPPING

| Framework | Control | Satisfied by |
|---|---|---|
| **NERC CIP-007-6** | R2 Security Patch Management | Trivy flags unpatched base images |
| | R5 System Access Control | No-root, no-privilege-escalation policies |
| **NERC CIP-010-4** | R1 Configuration Change Management | Admission control is change control at runtime |
| **NIST SP 800-53 Rev 5** | CM-6 Configuration Settings | Pod Security Standards baseline |
| | CM-7 Least Functionality | Dropped capabilities, no host namespaces |
| | RA-5 Vulnerability Scanning | Trivy |
| | SI-2 Flaw Remediation | Severity gate blocks the deploy |
| | SC-39 Process Isolation | runAsNonRoot, readOnlyRootFilesystem |
| **NIST CSF 2.0** | PR.PS-01 Configuration management | Policy enforcement |
| **CIS Kubernetes Benchmark** | Section 5 Policies | Each Kyverno rule below |
| **NSA/CISA Kubernetes Hardening Guidance** | Pod security, least privilege | The policy set |

---

## SETUP

```bash
brew install kind kubectl helm trivy

kind create cluster --name seclab

helm repo add kyverno https://kyverno.github.io/kyverno
helm repo update
helm install kyverno kyverno/kyverno -n kyverno --create-namespace

kubectl -n kyverno get pods      # wait for Running
```

---

## STEP 1 — Deploy something bad, with nothing stopping it

`manifests/insecure-deployment.yaml` is a workload with six real
misconfigurations, each of which has caused a breach somewhere:

| # | Misconfiguration | Why it matters |
|---|---|---|
| 1 | `privileged: true` | Effectively root on the node |
| 2 | `runAsUser: 0` | Container runs as root |
| 3 | `allowPrivilegeEscalation: true` | setuid path to higher privilege |
| 4 | `hostNetwork: true` | Container sees the node's network namespace |
| 5 | `hostPath` mount of `/` | The whole node filesystem, writable |
| 6 | `image: nginx:latest` | Unpinned tag — unreproducible, unscannable |

```bash
kubectl create namespace workloads
kubectl apply -f manifests/insecure-deployment.yaml
kubectl -n workloads get pods
```

It runs. **EVIDENCE 1:** the running pod. The point of this screenshot is that
nothing objected.

---

## STEP 2 — Apply the policies and watch it get refused

```bash
kubectl delete -f manifests/insecure-deployment.yaml
kubectl apply -f policies/kyverno-baseline.yaml
kubectl get clusterpolicy

kubectl apply -f manifests/insecure-deployment.yaml   # expect rejection
```

The admission webhook refuses the manifest and names the rule and the control.

**EVIDENCE 2:** the rejection message. This is the lab's headline artifact — a
policy you wrote, refusing a workload, citing the control it violates.

---

## STEP 3 — Fix the workload

`manifests/secure-deployment.yaml` is the same application, conforming:
non-root, no privilege escalation, no host namespaces, all capabilities dropped,
read-only root filesystem, seccomp profile set, image pinned by digest, limits
declared.

```bash
kubectl apply -f manifests/secure-deployment.yaml
kubectl -n workloads get pods
```

**EVIDENCE 3:** accepted and running.

---

## STEP 4 — Pod Security Standards as the second layer

Kyverno is the policy you chose. Pod Security admission is the platform baseline
underneath it, and it is one label:

```bash
kubectl label namespace workloads \
  pod-security.kubernetes.io/enforce=restricted \
  pod-security.kubernetes.io/warn=restricted --overwrite
```

Re-apply the insecure manifest with Kyverno removed and it is still refused —
by the platform this time. Defense in depth means a control failing open is not
the end of the story.

---

## STEP 5 — Scan the image

```bash
trivy image --severity HIGH,CRITICAL nginx:latest
trivy image --severity HIGH,CRITICAL --exit-code 1 nginx:1.27.3-alpine
trivy config manifests/
```

`trivy config` scans the manifests themselves — the same findings the admission
controller would produce, but at authoring time rather than deploy time. Shift
left is not a slogan here, it is literally the same check moved earlier.

**EVIDENCE 4:** the scan output, and the non-zero exit code that would fail a
build.

---

## STEP 6 — Tear down

```bash
kind delete cluster --name seclab
```

---

## KYVERNO OR OPA/GATEKEEPER?

You will be asked, because the job posting names OPA.

Both are admission controllers. **Gatekeeper** uses Rego — the same language as
the Lab A policies — which means one policy language across infrastructure,
pipeline and cluster, and that consolidation is a real operational argument.
**Kyverno** policies are Kubernetes resources written in YAML, so the learning
curve is near zero for a team that already knows Kubernetes, and it can mutate
and generate resources, not only validate them.

The honest answer: Kyverno for a Kubernetes-only team that wants adoption,
Gatekeeper where Rego is already the standard elsewhere. This lab uses Kyverno
precisely *because* Lab A already proves Rego — showing two policy engines is
worth more than showing one twice.

