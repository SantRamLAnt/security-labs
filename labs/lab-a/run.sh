#!/usr/bin/env bash
# LAB A runner. Own Azure subscription only. Never point this at employer infra.
set -u
BOLD=$'\033[1m'; RED=$'\033[31m'; GRN=$'\033[32m'; OFF=$'\033[0m'
say(){ printf "\n%s==> %s%s\n" "$BOLD" "$1" "$OFF"; }

say "0. Confirming you are in your OWN subscription"
az account show --query "{name:name, user:user.name}" -o tsv || { echo "Run: az login"; exit 1; }
read -r -p "Is that YOUR personal subscription? [y/N] " ok
[ "$ok" = "y" ] || { echo "Stopping. Use a personal subscription."; exit 1; }

say "1. Planning the INSECURE baseline (not applying it)"
( cd insecure && terraform init -input=false -no-color && \
  terraform plan -input=false -no-color -out=tfplan.binary && \
  terraform show -json tfplan.binary > ../tfplan.json )

say "2. Scanner findings — EVIDENCE 1 (screenshot this)"
checkov -f insecure/main.tf --compact 2>/dev/null || echo "(checkov not installed)"
tfsec insecure/ --no-colour 2>/dev/null || echo "(tfsec not installed)"

say "3. YOUR policy refusing the deploy — EVIDENCE 2 (screenshot this)"
conftest test tfplan.json -p policy/ && echo "${RED}Unexpected: policy passed${OFF}"

say "4. Planning the REMEDIATED baseline"
( cd secure && terraform init -input=false -no-color && \
  terraform plan -input=false -no-color -out=tfplan.binary && \
  terraform show -json tfplan.binary > ../tfplan-secure.json )

say "5. Policy passing — EVIDENCE 3 (screenshot this)"
conftest test tfplan-secure.json -p policy/ && echo "${GRN}PASS — baseline conforms${OFF}"

say "Next: cd secure && terraform apply   then verify, then terraform destroy"
