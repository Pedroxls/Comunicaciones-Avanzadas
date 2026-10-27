# Funciones compartidas de las políticas de firewall.
# Un puerto está abierto a internet si una regla de entrada lo permite desde
# 0.0.0.0/0 o ::/0. Sin lista de puertos, o con protocolo "all", GCP permite todos.
package lib.firewall

import rego.v1

internet := {"0.0.0.0/0", "::/0"}

cambios contains rc if {
	some rc in input.resource_changes
	rc.type == "google_compute_firewall"
	evaluar_cambio(rc)
	rc.change.after.direction == "INGRESS"
	not rc.change.after.disabled
}

evaluar_cambio(rc) if {
	some accion in rc.change.actions
	accion in {"create", "update"}
}

puerto_abierto(rc, puerto) if {
	algun_rango_de_internet(rc)
	some regla in rc.change.after.allow
	protocolo_tcp_o_todos(regla)
	puerto_en_regla(regla, puerto)
}

algun_rango_de_internet(rc) if {
	some rango in rc.change.after.source_ranges
	rango in internet
}

protocolo_tcp_o_todos(regla) if {
	regla.protocol in {"tcp", "all", "6"}
}

# Protocolo "all": no se pueden acotar puertos.
puerto_en_regla(regla, _) if {
	regla.protocol == "all"
}

# TCP sin puertos: GCP abre todos los puertos TCP.
puerto_en_regla(regla, _) if {
	regla.protocol in {"tcp", "6"}
	count(object.get(regla, "ports", [])) == 0
}

puerto_en_regla(regla, puerto) if {
	some spec in object.get(regla, "ports", [])
	puerto_en_spec(spec, puerto)
}

puerto_en_spec(spec, puerto) if {
	spec == sprintf("%d", [puerto])
}

puerto_en_spec(spec, puerto) if {
	is_number(spec)
	spec == puerto
}

puerto_en_spec(spec, puerto) if {
	is_string(spec)
	regex.match(`^\d+-\d+$`, spec)
	partes := split(spec, "-")
	puerto >= to_number(partes[0])
	puerto <= to_number(partes[1])
}

mensaje(control_id, severidad, rc, detalle) := sprintf("[%s][%s] %s: %s", [control_id, severidad, rc.address, detalle])
