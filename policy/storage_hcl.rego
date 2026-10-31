# LAB A/E — the same storage controls, evaluated against Terraform SOURCE (HCL).
#
# Why this file exists: storage.rego reads a terraform PLAN (input.resource_changes).
# In CI there is no Azure credential, so Gate 2 feeds conftest the raw .tf files.
# conftest parses HCL into a different shape (input.resource.<type>.<name>), so the
# plan-shaped policy found nothing to evaluate and reported "4 passed".
# Zero violations and zero rules evaluated printed identically. This policy closes
# that gap, and policy-tests/ pins it with an insecure and a secure HCL fixture.

package main

import rego.v1

hcl_storage contains [name, r] if {
	some name
	r := input.resource.azurerm_storage_account[name]
}

deny contains msg if {
	some [name, r] in hcl_storage
	r.allow_nested_items_to_be_public == true
	msg := sprintf("[CIS Azure: Storage public access] [NIST 800-53 SC-28] [NERC CIP-011-3 R1] azurerm_storage_account.%s permits public blob access", [name])
}

deny contains msg if {
	some [name, r] in hcl_storage
	r.min_tls_version != "TLS1_2"
	msg := sprintf("[CIS Azure: Minimum TLS] [NIST 800-53 SC-8] azurerm_storage_account.%s uses %v; TLS1_2 is the required minimum", [name, r.min_tls_version])
}

deny contains msg if {
	some [name, r] in hcl_storage
	r.https_traffic_only_enabled == false
	msg := sprintf("[CIS Azure: Secure transfer required] [NIST 800-53 SC-8] azurerm_storage_account.%s allows unencrypted HTTP", [name])
}

deny contains msg if {
	some [name, r] in hcl_storage
	not r.tags.teardown
	msg := sprintf("[NIST 800-53 CM-8 Asset Inventory] azurerm_storage_account.%s has no teardown tag; lab resources must be disposable", [name])
}
