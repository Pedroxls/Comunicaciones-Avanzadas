# CTL-RED-06 · Entrada desde internet a todos los puertos · severidad crítica (bloquea)
package red.todos_los_puertos

import rego.v1

import data.lib.firewall
import data.lib.plan

deny contains msg if {
	some rc in firewall.cambios
	abre_todos_los_puertos(rc)
	msg := plan.mensaje("CTL-RED-06", "critica", rc, "Entrada desde 0.0.0.0/0 o ::/0 a todos los puertos")
}

abre_todos_los_puertos(rc) if {
	firewall.algun_rango_de_internet(rc)
	some regla in rc.change.after.allow
	regla.protocol == "all"
}

abre_todos_los_puertos(rc) if {
	firewall.algun_rango_de_internet(rc)
	some regla in rc.change.after.allow
	regla.protocol in {"tcp", "udp", "6", "17"}
	count(object.get(regla, "ports", [])) == 0
}
