# CTL-LOG-01 · Auditoría de acceso a datos sin configurar · CIS 2.1 · severidad media (no bloquea)
package registro.audit_datos

import rego.v1

import data.lib.plan

warn contains msg if {
	some rc in plan.cambios_de("google_project")
	not hay_lectura_de_datos
	msg := plan.mensaje("CTL-LOG-01", "media", rc, "El plan crea el proyecto sin DATA_READ en la auditoría (CIS 2.1)")
}

warn contains msg if {
	some rc in plan.cambios_de("google_project_iam_audit_config")
	not config_tiene_lectura(rc)
	msg := plan.mensaje("CTL-LOG-01", "media", rc, "La auditoría no incluye DATA_READ (CIS 2.1)")
}

hay_lectura_de_datos if {
	some rc in plan.cambios_de("google_project_iam_audit_config")
	config_tiene_lectura(rc)
}

config_tiene_lectura(rc) if {
	configs := object.get(rc.change.after, "audit_log_config", [])
	some cfg in configs
	cfg.log_type == "DATA_READ"
}
