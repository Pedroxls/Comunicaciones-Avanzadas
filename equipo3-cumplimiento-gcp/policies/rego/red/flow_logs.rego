# CTL-RED-05 · Subred sin VPC Flow Logs · CIS GCP 3.10 · severidad media (no bloquea)
package red.flow_logs

import rego.v1

import data.lib.plan

warn contains msg if {
	some rc in plan.cambios_de("google_compute_subnetwork")
	not tiene_flow_logs(rc)
	msg := plan.mensaje("CTL-RED-05", "media", rc, "Subred sin VPC Flow Logs (CIS 3.10)")
}

tiene_flow_logs(rc) if {
	logs := object.get(rc.change.after, "log_config", [])
	is_array(logs)
	count(logs) > 0
}
