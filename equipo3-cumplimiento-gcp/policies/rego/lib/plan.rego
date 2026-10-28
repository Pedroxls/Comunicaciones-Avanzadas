# Cambios de un plan de Terraform que las políticas deben mirar.
package lib.plan

import rego.v1

cambios_de(tipo) := {rc |
	some rc in input.resource_changes
	rc.type == tipo
	evaluar(rc)
}

evaluar(rc) if {
	some accion in rc.change.actions
	accion in {"create", "update"}
}

mensaje(control_id, severidad, rc, detalle) := sprintf("[%s][%s] %s: %s", [control_id, severidad, rc.address, detalle])
