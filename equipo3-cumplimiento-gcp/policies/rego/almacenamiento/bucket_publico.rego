# CTL-STO-01 · Bucket con acceso público · CIS 5.1 · severidad crítica (bloquea)
package almacenamiento.bucket_publico

import rego.v1

import data.lib.plan

publicos := {"allUsers", "allAuthenticatedUsers"}

deny contains msg if {
	some rc in plan.cambios_de("google_storage_bucket_iam_member")
	rc.change.after.member in publicos
	msg := plan.mensaje("CTL-STO-01", "critica", rc, sprintf("Bucket expuesto a %s (CIS 5.1)", [rc.change.after.member]))
}

deny contains msg if {
	some rc in plan.cambios_de("google_storage_bucket_iam_binding")
	some miembro in rc.change.after.members
	miembro in publicos
	msg := plan.mensaje("CTL-STO-01", "critica", rc, sprintf("Bucket expuesto a %s (CIS 5.1)", [miembro]))
}
