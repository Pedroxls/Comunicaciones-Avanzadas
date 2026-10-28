# CTL-ETQ-01 · Sin las etiquetas obligatorias · severidad baja (no bloquea)
package gobierno.etiquetas

import rego.v1

import data.lib.plan

obligatorias := {"dueno", "ambiente", "clasificacion_datos", "centro_costos", "marco"}

# Solo tipos que en GCP aceptan labels. Firewall, VPC y subred no entran.
tipos := {
	"google_storage_bucket",
	"google_compute_instance",
	"google_cloud_run_v2_service",
	"google_bigquery_dataset",
	"google_pubsub_topic",
}

warn contains msg if {
	some tipo in tipos
	some rc in plan.cambios_de(tipo)
	count(faltantes(rc)) > 0
	msg := plan.mensaje("CTL-ETQ-01", "baja", rc, sprintf("Faltan etiquetas: %s", [concat(", ", faltantes(rc))]))
}

faltantes(rc) := [clave |
	some clave in obligatorias
	etiquetas := object.get(rc.change.after, "labels", {})
	is_object(etiquetas)
	object.get(etiquetas, clave, "") == ""
]
