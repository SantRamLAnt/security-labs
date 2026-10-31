# LAB J — Electronic Security Perimeter rules (NERC CIP-005-7), evaluated on Terraform source.
# The control-centre zone may be reached only through the intermediate system, every
# permission must carry its reason, nothing in the zone gets a public address, and the
# default is deny — written down, not assumed.
package esp

import rego.v1

intermediate_prefix := input.resource.azurerm_subnet.intermediate.address_prefixes[0]

cc_rules contains [name, r] if {
	some name
	r := input.resource.azurerm_network_security_rule[name]
	contains(r.network_security_group_name, "control_centre")
}

# E1 — inbound access to the control centre only from the intermediate system
deny contains msg if {
	some [name, r] in cc_rules
	r.direction == "Inbound"
	r.access == "Allow"
	r.source_address_prefix != intermediate_prefix
	msg := sprintf("[NERC CIP-005-7 R1.2, R2.1] [NIST SC-7, AC-17] %s allows inbound to the control-centre zone from %s; only the intermediate system (%s) may cross the perimeter", [name, r.source_address_prefix, intermediate_prefix])
}

# E2 — every allow carries a documented reason
deny contains msg if {
	some [name, r] in cc_rules
	r.access == "Allow"
	not r.description
	msg := sprintf("[NERC CIP-005-7 R1.3] %s grants access with no documented reason; CIP-005 R1.3 requires the reason for every permission", [name])
}

# E3 — nothing in the control-centre zone is publicly addressable
deny contains msg if {
	some name
	ip := input.resource.azurerm_public_ip[name]
	ip.tags.zone == "control-centre"
	msg := sprintf("[NERC CIP-005-7 R1.1] [NIST SC-7(4)] azurerm_public_ip.%s puts a public address inside the control-centre zone", [name])
}

# E4 — default deny, explicit
deny contains msg if {
	count(cc_rules) > 0
	not explicit_deny_all
	msg := "[NERC CIP-005-7 R1.3] [NIST SC-7(5)] the control-centre NSG has no explicit deny-all inbound rule; deny-by-default must be stated, not inherited"
}

explicit_deny_all if {
	some [_, r] in cc_rules
	r.direction == "Inbound"
	r.access == "Deny"
	r.source_address_prefix == "*"
	r.destination_port_range == "*"
}
