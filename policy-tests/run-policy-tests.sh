#!/usr/bin/env bash
# LAB A — unit tests for the OPA policy.
#
# WHY THIS FILE EXISTS
# A policy that has never been tested is a policy you are trusting on faith,
# and a policy gate that is wrong is worse than no gate — it fails open
# silently while everyone believes a control is in place.
#
# These fixtures are terraform-plan JSON shaped by hand, which means the policy
# can be tested without an Azure subscription, without credentials, and in
# under a second. That makes it runnable in CI on every commit to the policy
# itself. Policy as code is only code if it is tested like code.
#
# Four cases, each pinning down a different behaviour:
#   insecure  — all three misconfigurations        → exactly 3 denials
#   secure    — the remediated baseline            → 0 denials
#   untagged  — conforming but missing teardown    → exactly 1 denial
#   noop      — bad config, but action is "no-op"  → 0 denials
#   hcl-bad   — insecure Terraform SOURCE (what CI sees) → exactly 3 denials
#   hcl-good  — remediated Terraform SOURCE            → 0 denials
#
# The last one is the test that matters most and is the one people forget.
# The policy only evaluates create and update actions. Without this fixture,
# a regression that made the policy fire on every plan — including unchanged
# resources — would pass unnoticed until it blocked an unrelated deployment.

set -uo pipefail

# Layout is overridable so this script works both inside lab-a and after the
# files are copied into a CI repository with a different directory structure.
HERE="$(cd "$(dirname "$0")" && pwd)"
TEST_DIR="${TEST_DIR:-$HERE}"
POLICY_DIR="${POLICY_DIR:-$HERE/../policy}"

if [[ ! -d "$POLICY_DIR" ]]; then
  echo "  policy directory not found: $POLICY_DIR" >&2
  echo "  set POLICY_DIR to the directory containing storage.rego" >&2
  exit 2
fi

PASS=0
FAIL=0

check() {
  local name="$1" fixture="$2" expected="$3"
  local out count
  out=$(conftest test "${TEST_DIR}/${fixture}" -p "${POLICY_DIR}" --no-color 2>&1)
  count=$(grep -c '^FAIL' <<<"$out" || true)
  if [[ "$count" == "$expected" ]]; then
    printf '  PASS  %-10s %s denial(s)\n' "$name" "$count"
    PASS=$((PASS+1))
  else
    printf '  FAIL  %-10s expected %s denial(s), got %s\n' "$name" "$expected" "$count"
    sed 's/^/        /' <<<"$out"
    FAIL=$((FAIL+1))
  fi
}

echo
echo "  Lab A — OPA policy unit tests"
echo "  -----------------------------"
check insecure tfplan-insecure.json 3
check secure   tfplan-secure.json   0
check untagged tfplan-untagged.json 1
check noop     tfplan-noop.json     0
check hcl-bad  hcl-insecure/main.tf 3
check hcl-good hcl-secure/main.tf   0
echo
echo "  ${PASS} passed, ${FAIL} failed"
echo
[[ "$FAIL" -eq 0 ]]
