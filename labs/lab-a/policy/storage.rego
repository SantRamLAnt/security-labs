# LAB A — Policy as Code
# Denial messages cite the control they enforce, so a failed build tells the
# engineer WHICH control they broke, not just that something is wrong.

package main

import rego.v1

storage_changes contains r if {
	r := input.resource_changes[_]
	r.type == "azurerm_storage_account"
	r.change.actions[_] in {"create", "update"}
}

deny contains msg if {
	r := storage_changes[_]
	r.change.after.allow_nested_items_to_be_public == true
	msg := sprintf(
		"[CIS Azure: Storage public access] [NIST 800-53 SC-28] [NERC CIP-011-3 R1] %s permits public blob access",
		[r.address],
	)
}

deny contains msg if {
	r := storage_changes[_]
	r.change.after.min_tls_version != "TLS1_2"
	msg := sprintf(
		"[CIS Azure: Minimum TLS] [NIST 800-53 SC-8] %s uses %s; TLS1_2 is the required minimum",
		[r.address, r.change.after.min_tls_version],
	)
}

deny contains msg if {
	r := storage_changes[_]
	r.change.after.https_traffic_only_enabled == false
	msg := sprintf(
		"[CIS Azure: Secure transfer required] [NIST 800-53 SC-8] %s allows unencrypted HTTP",
		[r.address],
	)
}

deny contains msg if {
	r := storage_changes[_]
	not r.change.after.tags.teardown
	msg := sprintf(
		"[NIST 800-53 CM-8 Asset Inventory] %s has no teardown tag; lab resources must be disposable",
		[r.address],
	)
}
