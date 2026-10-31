#!/usr/bin/env bash
# LAB I teardown: remove the subscription activity-log export, then the whole resource group.
set -uo pipefail
az monitor diagnostic-settings subscription delete -n seclab-activity-to-law --yes
az group delete -n rg-seclab-siem --yes
az group exists -n rg-seclab-siem
az monitor diagnostic-settings subscription list --query "value[].name" -o tsv
