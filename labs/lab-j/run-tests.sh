#!/usr/bin/env bash
# LAB J: policy tests, then the matrix analysis. Each fixture must produce an EXACT number of denials:
# a known-bad file that suddenly passes means a rule stopped evaluating (fails open),
# which prints the same "0 failures" as a genuinely clean file.
set -uo pipefail
cd "$(dirname "$0")"
C="${CONFTEST:-conftest}"
fails=0
check() {  # name  namespace  file  expected
  n=$("$C" test "$3" -p policy --namespace "$2" --no-color 2>/dev/null | grep -c '^FAIL')
  if [ "$n" -eq "$4" ]; then r=PASS; else r=FAIL; fails=$((fails+1)); fi
  printf '  %s  %-22s %d denial(s), expected %d\n' "$r" "$1" "$n" "$4"
}
echo "  Lab J: grid model and perimeter policy tests"
echo "  ---------------------------------------------"
check grid-normal    gridmodel grid/feeder-normal.yaml       0
check grid-bad       gridmodel grid/feeder-bad.yaml          6
check grid-island    gridmodel grid/feeder-island.yaml       0   # passes every rule; topology.py catches it
check esp-secure     esp       infra/esp-secure/main.tf      0
check esp-insecure   esp       infra/esp-insecure/main.tf    5
echo
[ "$fails" -eq 0 ] && echo "  5 policy checks passed" || echo "  $fails policy check(s) failed"
echo
echo "  Lab J: the feeder as a matrix (grid/topology.py)"
echo "  ------------------------------------------------"
python3 grid/test_topology.py; t=$?
for f in normal bad island; do echo; python3 grid/topology.py grid/feeder-$f.yaml; done
exit $((fails + t))
