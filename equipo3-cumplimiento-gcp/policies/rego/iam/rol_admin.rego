# CTL-IAM-02 · Cuenta con rol Owner, Editor o de administrador · CIS 1.5 · severidad alta (bloquea)
package iam.rol_admin

import rego.v1

import data.lib.plan

tipos := {"google_project_iam_member", "google_project_iam_binding"}

deny contains msg if {
	some tipo in tipos
	some rc in plan.cambios_de(tipo)
	rol_privilegiado(rc.change.after.role)
	msg := plan.mensaje("CTL-IAM-02", "alta", rc, sprintf("Rol privilegiado %s (CIS 1.5)", [rc.change.after.role]))
}

rol_privilegiado(rol) if {
	rol in {"roles/owner", "roles/editor"}
}

rol_privilegiado(rol) if {
	contains(lower(rol), "admin")
}
