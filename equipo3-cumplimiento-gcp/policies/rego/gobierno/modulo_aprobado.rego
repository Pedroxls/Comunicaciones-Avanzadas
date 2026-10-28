# CTL-GOB-02 · Recurso de red o almacenamiento fuera de un módulo aprobado · severidad media (no bloquea)
package gobierno.modulo_aprobado

import rego.v1

import data.lib.plan

tipos := {
	"google_compute_network",
	"google_compute_subnetwork",
	"google_compute_firewall",
	"google_storage_bucket",
}

prefijos_aprobados := {
	"module.network.",
	"module.logging.",
	"module.evidence.",
	"module.agent.",
}

warn contains msg if {
	some tipo in tipos
	some rc in plan.cambios_de(tipo)
	not en_modulo_aprobado(rc.address)
	msg := plan.mensaje("CTL-GOB-02", "media", rc, "Recurso fuera de un módulo aprobado")
}

en_modulo_aprobado(address) if {
	some prefijo in prefijos_aprobados
	startswith(address, prefijo)
}
