#!/usr/bin/env bash
# LAB E — run gates 1-4 against the checked-out tree and report every result.
# Unlike the GitHub workflow (one job per gate), this runs them all in one shell,
# so any CI system (Harness, a laptop) can call it. Exit code = number of gates failed.
# Tools are downloaded into ./.tools at pinned versions.
set -uo pipefail
T="$PWD/.tools"; mkdir -p "$T"; export PATH="$T:$PATH"
fetch() { curl -sSL "$1" | tar xz -C "$T" "$2"; }
command -v gitleaks >/dev/null || fetch https://github.com/gitleaks/gitleaks/releases/download/v8.21.2/gitleaks_8.21.2_linux_x64.tar.gz gitleaks
command -v conftest >/dev/null || fetch https://github.com/open-policy-agent/conftest/releases/download/v0.56.0/conftest_0.56.0_Linux_x86_64.tar.gz conftest
command -v trivy    >/dev/null || fetch https://github.com/aquasecurity/trivy/releases/download/v0.76.1/trivy_0.76.1_Linux-64bit.tar.gz trivy
command -v checkov  >/dev/null || python3 -m pip install --quiet --user checkov >/dev/null 2>&1
command -v semgrep  >/dev/null || python3 -m pip install --quiet --user semgrep >/dev/null 2>&1
export PATH="$HOME/.local/bin:$PATH"

results=(); fails=0
gate() {
  local name="$1"; shift
  echo; echo "::::: $name"
  if "$@"; then results+=("PASS  $name"); else results+=("FAIL  $name"); fails=$((fails+1)); fi
}
gate "Gate 1 secrets (gitleaks, full history)" gitleaks git . --config .gitleaks.toml --redact --no-banner
gate "Gate 2 IaC (Checkov)"                     checkov --directory infra/ --framework terraform --compact --quiet
gate "Gate 2 IaC (Conftest, own OPA policy)"    conftest test infra/ -p policy/ --all-namespaces --no-color
gate "Gate 3 SAST (Semgrep)"                    semgrep scan --config p/python --config p/secrets --error --metrics=off --quiet app/
gate "Gate 4 dependencies (Trivy)"              trivy fs app/ --scanners vuln --severity CRITICAL,HIGH --ignore-unfixed --exit-code 1 --no-progress --quiet

echo; echo "=========== RESULT @ $(git log -1 --format='%h %s' 2>/dev/null)"
printf '%s\n' "${results[@]}"
echo "gates failed: $fails of ${#results[@]}"
exit "$fails"
