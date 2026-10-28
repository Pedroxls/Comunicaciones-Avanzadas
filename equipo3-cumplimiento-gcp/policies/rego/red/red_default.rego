# CTL-RED-03 · Existe la red default · CIS GCP 3.1 · severidad media (no bloquea)
package red.red_default

import rego.v1

import data.lib.plan

warn contains msg if {
	some rc in plan.cambios_de("google_compute_network")
	rc.change.after.name == "default"
	msg := plan.mensaje("CTL-RED-03", "media", rc, "Existe la red default (CIS 3.1)")
}
