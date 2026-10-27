# CTL-RED-01 · SSH (22/tcp) abierto a internet · CIS GCP 3.6 · severidad alta (bloquea)
package red.ssh_abierto

import rego.v1

import data.lib.firewall

deny contains msg if {
	some rc in firewall.cambios
	firewall.puerto_abierto(rc, 22)
	msg := firewall.mensaje("CTL-RED-01", "alta", rc, "SSH (22/tcp) abierto a 0.0.0.0/0 (CIS 3.6)")
}
