#!/usr/bin/env bash
# LAB I — triage the incidents the rules raised (steps 1-3 of README "STEP 4"),
# and, with --close, record the determination and close one incident (steps 4-5).
#
#   bash labs/lab-i/triage.sh                          # triage + scope, read-only
#   bash labs/lab-i/triage.sh --close <n> "<note>"     # comment + close incident <n> as BenignPositive
#
# Caller e-mail addresses are masked and subscription ids stripped, so the output can be published.
set -uo pipefail
RG=rg-seclab-siem; LAW=law-seclab; API=2024-03-01
SUB=$(az account show --query id -o tsv)
W=$(az monitor log-analytics workspace show -g "$RG" -n "$LAW" --query customerId -o tsv)
SI="https://management.azure.com/subscriptions/$SUB/resourceGroups/$RG/providers/Microsoft.OperationalInsights/workspaces/$LAW/providers/Microsoft.SecurityInsights"
MASK='extend Caller = iff(Caller has "@", strcat(substring(Caller, 0, 3), "***@", tostring(split(Caller, "@")[1])), Caller)'

incidents() {
  printf '\n$ incidents\n'
  az rest --method get --url "$SI/incidents?api-version=$API" \
    --query "sort_by(value, &properties.incidentNumber)[].{n:properties.incidentNumber, title:properties.title, severity:properties.severity, status:properties.status, classification:properties.classification, created:properties.createdTimeUtc}" -o table
}
q() { printf '\n$ %s\n' "$1"; az monitor log-analytics query -w "$W" --analytics-query "$2" -o table; }

if [ "${1:-}" = "--close" ]; then
  N="$2"; NOTE="$3"
  NAME=$(az rest --method get --url "$SI/incidents?api-version=$API" --query "value[?properties.incidentNumber==\`$N\`].name | [0]" -o tsv)
  # comment first (it bumps the incident etag), then read the incident fresh and close it
  json_comment=$(python3 -c 'import json,sys; print(json.dumps({"properties":{"message":sys.argv[1]}}))' "$NOTE")
  [ -n "${SKIP_COMMENT:-}" ] || az rest --method put --url "$SI/incidents/$NAME/comments/$(cat /proc/sys/kernel/random/uuid)?api-version=$API" --body "$json_comment" -o none
  az rest --method get --url "$SI/incidents/$NAME?api-version=$API" > /tmp/inc.json
  python3 - "$NOTE" <<'PY'
import json, sys
inc = json.load(open("/tmp/inc.json"))
p = inc["properties"]
body = {"etag": inc.get("etag"), "properties": {
    "title": p["title"], "severity": p["severity"], "status": "Closed",
    "classification": "BenignPositive", "classificationReason": "SuspiciousButExpected",
    "classificationComment": sys.argv[1][:1000]}}
json.dump(body, open("/tmp/inc-close.json", "w"))
PY
  az rest --method put --url "$SI/incidents/$NAME?api-version=$API" --body @/tmp/inc-close.json -o none
  incidents
  exit 0
fi

incidents
q "1 TRIAGE  every row the role-assignment rule matches: when, who, from where" \
  "AzureActivity | where OperationNameValue has 'ROLEASSIGNMENTS/WRITE' | where ActivityStatusValue in ('Success','Succeeded','Accepted') | where not(_ResourceId has '/resourceGroups/') | $MASK | project TimeGenerated, Caller, CallerIpAddress, Assignment = tostring(split(_ResourceId, '/')[-1]) | order by TimeGenerated asc"
q "2 SCOPE   everything each caller did 17:15-17:45 UTC (pivot on caller, not a guess)" \
  "AzureActivity | where TimeGenerated between (datetime(2026-10-31T17:15:00Z) .. datetime(2026-10-31T17:45:00Z)) | where ActivityStatusValue in ('Success','Succeeded','Accepted') | $MASK | summarize events = count() by Caller, OperationNameValue | order by Caller asc, OperationNameValue asc"
q "3 COVERAGE  the events each deployed rule looks for, as they reached the workspace" \
  "AzureActivity | where OperationNameValue has_any ('LISTKEYS', 'POLICYASSIGNMENTS/DELETE', 'ROLEASSIGNMENTS/WRITE') | where ActivityStatusValue in ('Success','Succeeded') | summarize events = count(), newest = max(TimeGenerated) by OperationNameValue"
