#!/usr/bin/env bash
# LAB I — stand up Sentinel on Azure Activity only, deploy the three AzureActivity
# rules from rules/, then generate the telemetry each one should catch.
# Run from Azure Cloud Shell (bash), in your OWN subscription.
#
# Cost controls (see README "COST"):
#   - Azure Activity is a free data source in Sentinel; no other connector is enabled.
#   - The workspace is created with a daily ingestion cap (--quota, GB/day).
#   - Everything lives in rg-seclab-siem (teardown=true); run teardown.sh afterwards.
#
# The two other rules are NOT deployed, on purpose:
#   detect-openai-volume-anomaly.kql  needs AzureDiagnostics from the OpenAI account (extra ingestion)
#   detect-legacy-auth-signin.kql     needs the Entra ID SigninLogs connector (expensive)
set -euo pipefail

RG=rg-seclab-siem
LAW=law-seclab
LOC=eastus
API=2024-03-01
HERE="$(cd "$(dirname "$0")" && pwd)"

SUB=$(az account show --query id -o tsv)
WS_ID="/subscriptions/$SUB/resourceGroups/$RG/providers/Microsoft.OperationalInsights/workspaces/$LAW"
SI="https://management.azure.com$WS_ID/providers/Microsoft.SecurityInsights"

step() { printf '\n$ %s\n' "$*"; }

step "register Microsoft.SecurityInsights"
az provider register --namespace Microsoft.SecurityInsights --wait -o none
az provider show -n Microsoft.SecurityInsights --query registrationState -o tsv

step "resource group + workspace with a daily cap of 0.1 GB"
az group create -n "$RG" -l "$LOC" --tags teardown=true lab=lab-i -o none
az monitor log-analytics workspace create -g "$RG" -n "$LAW" -l "$LOC" \
  --retention-time 30 --quota 0.1 --tags teardown=true lab=lab-i -o none
az monitor log-analytics workspace show -g "$RG" -n "$LAW" \
  --query "{workspace:name, dailyCapGB:workspaceCapping.dailyQuotaGb, retentionDays:retentionInDays, sku:sku.name}" -o table

step "enable Microsoft Sentinel on the workspace"
az rest --method put --url "$SI/onboardingStates/default?api-version=$API" \
  --body '{"properties":{}}' --query "{name:name, type:type}" -o table

step "Azure Activity connector: subscription activity log -> workspace (the free data source)"
az monitor diagnostic-settings subscription create -n seclab-activity-to-law --location "$LOC" \
  --workspace "$WS_ID" \
  --logs '[{"category":"Administrative","enabled":true},{"category":"Security","enabled":true},{"category":"Policy","enabled":true},{"category":"Alert","enabled":true}]' -o none
az monitor diagnostic-settings subscription list --query "value[?name=='seclab-activity-to-law'].{name:name, categories:length(logs[?enabled])}" -o table

step "deploy the three AzureActivity analytics rules from rules/"
python3 - "$HERE/rules" > /tmp/lab-i-rules.tsv <<'PY'
import json, sys, uuid, pathlib
rules_dir = pathlib.Path(sys.argv[1])
ents = [
  {"entityType": "Account", "fieldMappings": [{"identifier": "FullName", "columnName": "Caller"}]},
  {"entityType": "IP", "fieldMappings": [{"identifier": "Address", "columnName": "CallerIpAddress"}]},
  {"entityType": "AzureResource", "fieldMappings": [{"identifier": "ResourceId", "columnName": "_ResourceId"}]},
]
spec = [
  ("detect-cognitive-key-listed",       "Cognitive Services / Azure OpenAI account key listed", "Medium", ["CredentialAccess"], ["T1552"]),
  ("detect-policy-assignment-removed",  "Azure Policy assignment deleted, or exemption created", "High", ["DefenseEvasion"], ["T1562"]),
  ("detect-privileged-role-assignment", "Privileged role assigned at subscription scope", "High", ["PrivilegeEscalation", "Persistence"], ["T1098"]),
]
for slug, name, sev, tactics, techniques in spec:
    text = (rules_dir / f"{slug}.kql").read_text()
    # the query is every non-comment line; the comment blocks stay in the repo file
    query = "\n".join(l for l in text.splitlines() if not l.lstrip().startswith("//")).strip()
    body = {"kind": "Scheduled", "properties": {
        "displayName": f"[Lab I] {name}",
        "description": f"Source: labs/lab-i/rules/{slug}.kql (github.com/SantRamLAnt/security-labs)",
        "severity": sev, "enabled": True, "query": query,
        "queryFrequency": "PT15M", "queryPeriod": "PT1H",
        "triggerOperator": "GreaterThan", "triggerThreshold": 0,
        "suppressionDuration": "PT1H", "suppressionEnabled": False,
        "tactics": tactics, "techniques": techniques, "entityMappings": ents,
        "incidentConfiguration": {"createIncident": True, "groupingConfiguration": {
            "enabled": False, "reopenClosedIncident": False, "lookbackDuration": "PT5H",
            "matchingMethod": "AllEntities", "groupByEntities": [], "groupByAlertDetails": [], "groupByCustomDetails": []}},
    }}
    rid = str(uuid.uuid5(uuid.NAMESPACE_URL, "seclab/lab-i/" + slug))
    path = f"/tmp/lab-i-{slug}.json"
    pathlib.Path(path).write_text(json.dumps(body))
    print(f"{rid}\t{path}")
PY
while IFS=$'\t' read -r rid path; do
  az rest --method put --url "$SI/alertRules/$rid?api-version=$API" --body "@$path" -o none \
    || echo "RULE NOT CREATED: $path (re-run this step once AzureActivity has data)"
done < /tmp/lab-i-rules.tsv
az rest --method get --url "$SI/alertRules?api-version=$API" \
  --query "value[].{rule:properties.displayName, severity:properties.severity, enabled:properties.enabled, tactics:join(',', properties.tactics), every:properties.queryFrequency}" -o table

step "generate the telemetry (ground-truth action log, UTC)"
ME=$(az ad signed-in-user show --query id -o tsv)
log() { printf '%s  %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*"; }

log "ACTION 1  list keys on oai-seclab-lsr01 (output discarded, never printed)  -> expect: key listed"
az cognitiveservices account keys list -n oai-seclab-lsr01 -g rg-seclab-ai -o none

log "ACTION 2  create, then delete, a throwaway policy assignment            -> expect: policy assignment deleted"
az policy assignment create -n seclab-detect-canary --display-name "seclab-detect-canary (Lab I, deleted immediately)" \
  --policy 06a78e20-9358-41c9-923c-fb736d382a4d --scope "/subscriptions/$SUB/resourceGroups/$RG" -o none
az policy assignment delete -n seclab-detect-canary --scope "/subscriptions/$SUB/resourceGroups/$RG"

log "ACTION 3  add, then remove, Reader for myself at SUBSCRIPTION scope       -> expect: privileged role assignment"
az role assignment create --assignee-object-id "$ME" --assignee-principal-type User --role Reader --scope "/subscriptions/$SUB" -o none
az role assignment delete --assignee "$ME" --role Reader --scope "/subscriptions/$SUB"

log "done. Activity log -> workspace lags several minutes; rules run every 15 minutes."
