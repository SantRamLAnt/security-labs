# LAB J — the distribution network model as configuration, gated like code.
#
# A feeder's normal configuration (which devices exist, which phases they carry, what is
# normally open) is an operational baseline. Changing it without review is exactly the
# unauthorised configuration change NERC CIP-010-4 R1 exists to prevent, and a wrong record
# is a field-safety problem before it is a compliance one.
#
# These are SCREENING rules for a synthetic model. They are not a protection coordination
# study, a load flow, or switching authority; they catch record errors before a human
# engineer has to.
package gridmodel

import rego.v1

devices contains [f.id, d] if {
	some f in input.feeders
	some d in f.devices
}

by_id[d.id] := d if some [_, d] in devices

# R1 — change control: every change carries an authorisation
deny contains msg if {
	not input.change.switching_order
	msg := "[NERC CIP-010-4 R1.2] [NIST CM-3] change has no switching order / change ticket: an unauthorised change to the network baseline"
}

deny contains msg if {
	not input.change.approved_by
	msg := "[NERC CIP-010-4 R1.2] [NIST CM-3, CM-5] change has no approver recorded"
}

# R2 — radial operation: a tie between two feeders must be normally open
deny contains msg if {
	some [fid, d] in devices
	d.ties_to
	d.normal != "open"
	msg := sprintf("[Radial design] %s on %s ties to %s and is normally %s: two sources in parallel, so the network is no longer radial and protection assumptions break", [d.id, fid, d.ties_to, d.normal])
}

# R3 — one source per feeder
deny contains msg if {
	some f in input.feeders
	sources := [d.id | some d in f.devices; d.upstream == null]
	count(sources) != 1
	msg := sprintf("[Network model] feeder %s has %d source devices %v; a radial feeder has exactly one", [f.id, count(sources), sources])
}

# R4 — phase consistency: a device cannot carry a phase its upstream device does not
deny contains msg if {
	some [_, d] in devices
	up := by_id[d.upstream]
	some p in d.phases
	not p in up.phases
	msg := sprintf("[Phase connectivity] %s carries phase %s but its upstream device %s carries only %v", [d.id, p, up.id, up.phases])
}

# R5 — coordination screen: a downstream protective device must be rated below its upstream one
deny contains msg if {
	some [_, d] in devices
	d.rating_a
	up := by_id[d.upstream]
	up.rating_a
	d.rating_a >= up.rating_a
	msg := sprintf("[Protection screen] %s (%s, %d A) is rated at or above its upstream %s (%s, %d A); the upstream device may operate first and drop more customers than necessary", [d.id, d.type, d.rating_a, up.id, up.type, up.rating_a])
}
