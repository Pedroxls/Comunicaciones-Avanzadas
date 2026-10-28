# CTL-IAM-01 · Llave de cuenta de servicio administrada por el usuario · CIS 1.4 · severidad alta (bloquea)
package iam.llave_sa

import rego.v1

import data.lib.plan

deny contains msg if {
	some rc in plan.cambios_de("google_service_account_key")
	msg := plan.mensaje("CTL-IAM-01", "alta", rc, "Llave de cuenta de servicio administrada por el usuario (CIS 1.4)")
}
