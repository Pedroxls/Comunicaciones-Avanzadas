# CTL-RED-02 · RDP (3389/tcp) abierto a internet · CIS GCP 3.7 · severidad alta (bloquea)
package red.rdp_abierto

import rego.v1

import data.lib.firewall

deny contains msg if {
	some rc in firewall.cambios
	firewall.puerto_abierto(rc, 3389)
	msg := firewall.mensaje("CTL-RED-02", "alta", rc, "RDP (3389/tcp) abierto a 0.0.0.0/0 (CIS 3.7)")
}
