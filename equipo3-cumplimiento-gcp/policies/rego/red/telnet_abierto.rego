# CTL-RED-04 · Telnet (23/tcp) abierto a internet · control propio · severidad alta (bloquea)
package red.telnet_abierto

import rego.v1

import data.lib.firewall

deny contains msg if {
	some rc in firewall.cambios
	firewall.puerto_abierto(rc, 23)
	msg := firewall.mensaje("CTL-RED-04", "alta", rc, "Telnet (23/tcp) abierto a 0.0.0.0/0; envía credenciales sin cifrar")
}
