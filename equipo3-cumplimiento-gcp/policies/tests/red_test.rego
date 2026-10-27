# Cada política tiene al menos un caso que pasa y uno que falla (Definition of Done de HU-02).
package red_test

import rego.v1

import data.red.rdp_abierto
import data.red.ssh_abierto
import data.red.telnet_abierto

plan_firewall(nombre, protocolo, puertos, rangos) := {"resource_changes": [{
	"address": sprintf("google_compute_firewall.%s", [nombre]),
	"type": "google_compute_firewall",
	"change": {
		"actions": ["create"],
		"after": {
			"name": nombre,
			"direction": "INGRESS",
			"source_ranges": rangos,
			"allow": [{"protocol": protocolo, "ports": puertos}],
		},
	},
}]}

tiene(resultado, control) if {
	some m in resultado
	startswith(m, sprintf("[%s]", [control]))
}

# CTL-RED-01 · SSH
test_ssh_abierto_a_internet_falla if {
	r := ssh_abierto.deny with input as plan_firewall("admin", "tcp", ["22"], ["0.0.0.0/0"])
	tiene(r, "CTL-RED-01")
}

test_ssh_solo_desde_vpn_pasa if {
	r := ssh_abierto.deny with input as plan_firewall("admin", "tcp", ["22"], ["10.8.0.0/16"])
	count(r) == 0
}

test_rango_de_puertos_que_incluye_ssh_falla if {
	r := ssh_abierto.deny with input as plan_firewall("rango", "tcp", ["20-30"], ["0.0.0.0/0"])
	tiene(r, "CTL-RED-01")
}

test_ssh_abierto_en_ipv6_falla if {
	r := ssh_abierto.deny with input as plan_firewall("admin6", "tcp", ["22"], ["::/0"])
	tiene(r, "CTL-RED-01")
}

# CTL-RED-02 · RDP
test_rdp_abierto_a_internet_falla if {
	r := rdp_abierto.deny with input as plan_firewall("escritorio", "tcp", ["3389"], ["0.0.0.0/0"])
	tiene(r, "CTL-RED-02")
}

test_rdp_desde_red_interna_pasa if {
	r := rdp_abierto.deny with input as plan_firewall("escritorio", "tcp", ["3389"], ["10.0.0.0/8"])
	count(r) == 0
}

# CTL-RED-04 · Telnet
test_telnet_abierto_a_internet_falla if {
	r := telnet_abierto.deny with input as plan_firewall("legacy", "tcp", ["23"], ["0.0.0.0/0"])
	tiene(r, "CTL-RED-04")
}

test_telnet_desde_red_interna_pasa if {
	r := telnet_abierto.deny with input as plan_firewall("legacy", "tcp", ["23"], ["10.0.0.0/8"])
	count(r) == 0
}

# Casos comunes a las tres políticas
test_https_publico_pasa if {
	entrada := plan_firewall("web", "tcp", ["443"], ["0.0.0.0/0"])
	(count(ssh_abierto.deny) + count(rdp_abierto.deny)) + count(telnet_abierto.deny) == 0 with input as entrada
}

# Sin lista de puertos se permiten todos: deben fallar los tres controles.
test_todos_los_puertos_falla_los_tres if {
	entrada := plan_firewall("todo", "all", [], ["0.0.0.0/0"])
	tiene(ssh_abierto.deny, "CTL-RED-01") with input as entrada
	tiene(rdp_abierto.deny, "CTL-RED-02") with input as entrada
	tiene(telnet_abierto.deny, "CTL-RED-04") with input as entrada
}

# Una regla de salida no se evalúa como acceso desde internet.
test_regla_de_salida_pasa if {
	entrada := plan_firewall("salida", "tcp", ["22"], ["0.0.0.0/0"])
	salida := json.patch(entrada, [{"op": "replace", "path": "/resource_changes/0/change/after/direction", "value": "EGRESS"}])
	count(ssh_abierto.deny) == 0 with input as salida
}

# Un recurso que se elimina no se evalúa.
test_regla_que_se_elimina_pasa if {
	entrada := plan_firewall("vieja", "tcp", ["22"], ["0.0.0.0/0"])
	borrado := json.patch(entrada, [{"op": "replace", "path": "/resource_changes/0/change/actions", "value": ["delete"]}])
	count(ssh_abierto.deny) == 0 with input as borrado
}
