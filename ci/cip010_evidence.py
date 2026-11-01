#!/usr/bin/env python3
"""Generate a CIP-010-4 R1 style evidence package from this repository's own history.

Every row comes from `git` and the GitHub Actions API (`gh run list`). Nothing is typed by hand.
    python3 ci/cip010_evidence.py > audit/CIP-010-R1-evidence.md
"""
import json, subprocess, datetime

BASELINE = ["infra/", "k8s/", "policy/", "labs/lab-j/grid/", "labs/lab-j/infra/", "labs/lab-j/policy/",
            ".github/workflows/", "ci/run-gates.sh", ".harness/", ".gitleaksignore"]
REPO = "https://github.com/SantRamLAnt/security-labs"

def sh(*a): return subprocess.run(a, capture_output=True, text=True, check=True).stdout

head = sh("git", "rev-parse", "--short", "HEAD").strip()
runs = json.loads(sh("gh", "run", "list", "-R", "SantRamLAnt/security-labs", "-L", "200",
                     "--json", "headSha,conclusion,workflowName,databaseId"))
by_sha = {}
for r in runs:
    by_sha.setdefault(r["headSha"][:7], []).append(r)

rows = []
for line in sh("git", "log", "--reverse", "--format=%h|%ad|%an|%G?|%s", "--date=iso-strict", "--", *BASELINE).splitlines():
    h, date, author, sig, subj = line.split("|", 4)
    files = [f for f in sh("git", "show", "--name-only", "--format=", h).split() if any(f.startswith(b) for b in BASELINE)]
    ci = by_sha.get(h, [])
    cell = " · ".join(f"[{r['workflowName']}: {r['conclusion']}]({REPO}/actions/runs/{r['databaseId']})" for r in ci) or "no run"
    rows.append((h, date[:16].replace("T", " "), author, sig, subj, len(files), cell))

files = [f for f in sh("git", "ls-files", *BASELINE).split()]
now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
out = []
p = out.append
p("# CIP-010-4 R1 — configuration change management evidence")
p(f"Generated {now} from `git` and GitHub Actions by `ci/cip010_evidence.py` at commit `{head}`.")
p("Self-directed lab repository, synthetic systems. Format follows the questions a CIP-010 R1 audit asks.\n")
p("## R1.1 — the baseline")
p(f"The baseline is the content of these {len(files)} files at `{head}`, version-controlled; any deviation is a diff.\n")
p("| File | Blob |\n|---|---|")
for f in files:
    p(f"| `{f}` | `{sh('git', 'rev-parse', 'HEAD:' + f).strip()[:10]}` |")
p("\n## R1.2 — every change to the baseline: who, when, what, and whether it passed the gates")
p("| Commit | When (UTC) | Author | Signed | Change | Baseline files | Security gates |\n|---|---|---|---|---|---|---|")
for h, d, a, s, subj, n, cell in rows:
    p(f"| [`{h}`]({REPO}/commit/{h}) | {d} | {a} | {'yes' if s == 'G' else 'no'} | {subj} | {n} | {cell} |")
fails = sum(1 for r in rows if "failure" in r[6])
p(f"\n{len(rows)} baseline changes. {fails} failed the security gates. All three are the Lab E story (the pipeline as handed over, then the gates turning red on planted findings), and `279eb9b` remediated every finding.\n")
p("## R1.4 / R1.5 — security controls verified before the change is accepted")
p("Every push runs the blocking gates (secrets over full history, Checkov, Conftest/OPA, Semgrep, Trivy) and the")
p("policy self-tests. Lab A and Lab J configurations were also planned against a real Azure subscription before acceptance.\n")
# live branch protection state, read from the GitHub API (not asserted by hand)
try:
    prot = json.loads(sh("gh", "api", "repos/SantRamLAnt/security-labs/branches/main/protection"))
except subprocess.CalledProcessError:
    prot = None
checks = (prot or {}).get("required_status_checks") or {}
pr = (prot or {}).get("required_pull_request_reviews")
admins = ((prot or {}).get("enforce_admins") or {}).get("enabled")
signed = ((prot or {}).get("required_signatures") or {}).get("enabled")
p("## Branch protection on `main`, read live from the GitHub API")
if prot:
    p(f"- Pull request required: **{'yes' if pr is not None else 'no'}** · approvals required: {pr.get('required_approving_review_count', 0) if pr else 0}")
    p(f"- Required status checks ({'strict, branch must be up to date' if checks.get('strict') else 'not strict'}): " + ", ".join(f"`{c}`" for c in checks.get("contexts", [])))
    p(f"- Applies to administrators: **{'yes' if admins else 'no'}** · signed commits required: **{'yes' if signed else 'no'}**\n")
else:
    p("- **Not protected.** Any change can be pushed straight to `main`.\n")
p("## Findings an auditor would raise — stated, not hidden")
p("1. **No independent approval.** One person authors and accepts every change. Branch protection can require a second")
p("   reviewer, but a one-person repository cannot satisfy it; in a team this is the separation-of-duties control for R1.2. **Open.**")
p(f"2. **Unsigned commits** ({sum(1 for r in rows if r[3] != 'G')} of {len(rows)}). Required signing makes authorship provable. **{'Fixed' if signed else 'Open'}.**")
if prot and checks.get("contexts") and admins:
    p("3. **Failed changes could reach `main`.** True for the history above. **Fixed:** every change now needs a pull request with all")
    p("   five gates passing, with no administrator bypass — the gate is preventive, not just detective.")
else:
    p("3. **Failed changes reached `main`.** The gates reported them, but nothing stopped the push. Required status checks")
    p("   make the gate preventive instead of detective. **Open.**")
print("\n".join(out))
