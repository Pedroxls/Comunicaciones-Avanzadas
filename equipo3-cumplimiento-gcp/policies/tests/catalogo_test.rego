# Un caso que pasa y uno que falla por cada control del catálogo que no es de puerto.
package catalogo_test

import rego.v1

import data.almacenamiento.bucket_publico
import data.gobierno.etiquetas
import data.gobierno.modulo_aprobado
import data.iam.llave_sa
import data.iam.rol_admin
import data.red.flow_logs
import data.red.red_default
import data.red.todos_los_puertos
import data.registro.audit_datos

cambio(tipo, address, after) := {"resource_changes": [{
	"address": address,
	"type": tipo,
	"change": {"actions": ["create"], "after": after},
}]}

tiene(resultado, control) if {
	some m in resultado
	startswith(m, sprintf("[%s]", [control]))
}

# CTL-RED-03
test_red_default_falla if {
	r := red_default.warn with input as cambio("google_compute_network", "google_compute_network.default", {"name": "default"})
	tiene(r, "CTL-RED-03")
}

test_red_propia_pasa if {
	r := red_default.warn with input as cambio("google_compute_network", "module.network.google_compute_network.vpc", {"name": "dev-vpc"})
	count(r) == 0
}

# CTL-RED-05
test_subred_sin_flow_logs_falla if {
	r := flow_logs.warn with input as cambio("google_compute_subnetwork", "google_compute_subnetwork.abierta", {"name": "abierta", "log_config": []})
	tiene(r, "CTL-RED-05")
}

test_subred_con_flow_logs_pasa if {
	r := flow_logs.warn with input as cambio("google_compute_subnetwork", "module.network.google_compute_subnetwork.privada", {"name": "privada", "log_config": [{"metadata": "INCLUDE_ALL_METADATA"}]})
	count(r) == 0
}

# CTL-RED-06
test_todos_los_puertos_falla if {
	entrada := cambio("google_compute_firewall", "google_compute_firewall.todo", {
		"name": "todo",
		"direction": "INGRESS",
		"source_ranges": ["0.0.0.0/0"],
		"allow": [{"protocol": "all"}],
	})
	r := todos_los_puertos.deny with input as entrada
	tiene(r, "CTL-RED-06")
}

test_https_publico_no_es_todos_los_puertos if {
	entrada := cambio("google_compute_firewall", "module.network.google_compute_firewall.web", {
		"name": "web",
		"direction": "INGRESS",
		"source_ranges": ["0.0.0.0/0"],
		"allow": [{"protocol": "tcp", "ports": ["443"]}],
	})
	r := todos_los_puertos.deny with input as entrada
	count(r) == 0
}

test_deny_de_todos_los_puertos_no_dispara_el_control if {
	entrada := cambio("google_compute_firewall", "module.network.google_compute_firewall.denegar_entrada", {
		"name": "denegar",
		"direction": "INGRESS",
		"source_ranges": ["0.0.0.0/0"],
		"deny": [{"protocol": "all"}],
	})
	r := todos_los_puertos.deny with input as entrada
	count(r) == 0
}

# CTL-IAM-01
test_llave_de_cuenta_falla if {
	r := llave_sa.deny with input as cambio("google_service_account_key", "google_service_account_key.manual", {"service_account_id": "apps"})
	tiene(r, "CTL-IAM-01")
}

test_cuenta_sin_llave_pasa if {
	r := llave_sa.deny with input as cambio("google_service_account", "google_service_account.apps", {"account_id": "apps"})
	count(r) == 0
}

# CTL-IAM-02
test_rol_owner_falla if {
	r := rol_admin.deny with input as cambio("google_project_iam_member", "google_project_iam_member.dueno", {"role": "roles/owner", "member": "serviceAccount:apps@p.iam"})
	tiene(r, "CTL-IAM-02")
}

test_rol_viewer_pasa if {
	r := rol_admin.deny with input as cambio("google_project_iam_member", "google_project_iam_member.lectura", {"role": "roles/viewer", "member": "serviceAccount:apps@p.iam"})
	count(r) == 0
}

# CTL-LOG-01
test_proyecto_sin_auditoria_falla if {
	r := audit_datos.warn with input as cambio("google_project", "google_project.dev", {"project_id": "dev"})
	tiene(r, "CTL-LOG-01")
}

test_proyecto_con_data_read_pasa if {
	entrada := {"resource_changes": [
		{
			"address": "google_project.dev",
			"type": "google_project",
			"change": {"actions": ["create"], "after": {"project_id": "dev"}},
		},
		{
			"address": "google_project_iam_audit_config.datos",
			"type": "google_project_iam_audit_config",
			"change": {"actions": ["create"], "after": {"audit_log_config": [{"log_type": "DATA_READ"}]}},
		},
	]}
	r := audit_datos.warn with input as entrada
	count(r) == 0
}

# CTL-STO-01
test_bucket_publico_falla if {
	r := bucket_publico.deny with input as cambio("google_storage_bucket_iam_member", "google_storage_bucket_iam_member.publico", {"member": "allUsers", "role": "roles/storage.objectViewer"})
	tiene(r, "CTL-STO-01")
}

test_bucket_de_una_persona_pasa if {
	r := bucket_publico.deny with input as cambio("google_storage_bucket_iam_member", "google_storage_bucket_iam_member.equipo", {"member": "user:equipo@tec.mx", "role": "roles/storage.objectViewer"})
	count(r) == 0
}

# CTL-ETQ-01
test_bucket_sin_etiquetas_falla if {
	r := etiquetas.warn with input as cambio("google_storage_bucket", "google_storage_bucket.evidencia", {"name": "evidencia", "labels": {}})
	tiene(r, "CTL-ETQ-01")
}

test_bucket_con_etiquetas_pasa if {
	r := etiquetas.warn with input as cambio("google_storage_bucket", "module.evidence.google_storage_bucket.evidencia", {"name": "evidencia", "labels": {
		"dueno": "equipo3",
		"ambiente": "dev",
		"clasificacion_datos": "interno",
		"centro_costos": "curso",
		"marco": "cis",
	}})
	count(r) == 0
}

# CTL-GOB-02
test_firewall_suelto_falla if {
	r := modulo_aprobado.warn with input as cambio("google_compute_firewall", "google_compute_firewall.suelto", {"name": "suelto", "direction": "INGRESS"})
	tiene(r, "CTL-GOB-02")
}

test_firewall_del_modulo_pasa if {
	r := modulo_aprobado.warn with input as cambio("google_compute_firewall", "module.network.google_compute_firewall.iap_ssh", {"name": "dev-iap-ssh", "direction": "INGRESS"})
	count(r) == 0
}
