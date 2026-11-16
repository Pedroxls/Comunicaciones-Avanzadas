# Índice de la evidencia y datos del reporte. Las tablas solo reciben filas
# nuevas; las vistas de sql/ calculan el estado actual. Looker Studio se
# conecta a las vistas.

resource "google_bigquery_dataset" "cumplimiento" {
  dataset_id = "cumplimiento"
  location   = var.bq_location
  project    = var.project_id
  labels     = local.etiquetas

  depends_on = [google_project_service.apis]
}

locals {
  tablas = toset(["evaluacion", "hallazgo", "evidencia", "decision_agente"])

  # El catálogo vive en Git. Estas vistas lo exponen a BigQuery tal como está
  # en policies/catalog; se regeneran al aplicar el bootstrap.
  catalogo = yamldecode(file("${path.module}/../../policies/catalog/controls.yaml"))
  mapeos   = yamldecode(file("${path.module}/../../policies/catalog/mappings.yaml"))

  sql_controles = join(",\n  ", [
    for c in local.catalogo.controles : format(
      "STRUCT(%s AS control_id, %s AS titulo, %s AS dominio, %s AS severidad, %s AS bloquea, %s AS ref_cis)",
      jsonencode(c.control_id),
      jsonencode(c.titulo),
      jsonencode(c.dominio),
      jsonencode(c.severidad),
      c.bloquea ? "TRUE" : "FALSE",
      c.ref_cis == null ? "CAST(NULL AS STRING)" : jsonencode(c.ref_cis),
    )
  ])

  sql_mapeos = join(",\n  ", [
    for m in local.mapeos.mapeos : format(
      "STRUCT(%s AS control_id, %s AS marco_id, %s AS requisito)",
      jsonencode(m.control_id),
      jsonencode(m.marco_id),
      jsonencode(m.requisito),
    )
  ])

  sql_marcos = join(",\n  ", [
    for m in local.mapeos.marcos : format(
      "STRUCT(%s AS marco_id, %s AS nombre, %s AS version, %s AS tipo)",
      jsonencode(m.marco_id),
      jsonencode(m.nombre),
      m.version == null ? "CAST(NULL AS STRING)" : jsonencode(m.version),
      jsonencode(m.tipo),
    )
  ])

  vistas_catalogo = {
    catalogo_control = "SELECT * FROM UNNEST([\n  ${local.sql_controles}\n])"
    catalogo_marco   = "SELECT * FROM UNNEST([\n  ${local.sql_mapeos}\n])"
    marco            = "SELECT * FROM UNNEST([\n  ${local.sql_marcos}\n])"
  }
}

resource "google_bigquery_table" "tabla" {
  for_each = local.tablas

  dataset_id          = google_bigquery_dataset.cumplimiento.dataset_id
  table_id            = each.value
  project             = var.project_id
  deletion_protection = var.proteger_tablas
  schema              = file("${path.module}/schemas/${each.value}.json")
  labels              = local.etiquetas
}

resource "google_bigquery_table" "catalogo" {
  for_each = local.vistas_catalogo

  dataset_id          = google_bigquery_dataset.cumplimiento.dataset_id
  table_id            = each.key
  project             = var.project_id
  deletion_protection = var.proteger_tablas

  view {
    query          = each.value
    use_legacy_sql = false
  }
}

resource "google_bigquery_table" "evaluaciones" {
  dataset_id          = google_bigquery_dataset.cumplimiento.dataset_id
  table_id            = "evaluaciones"
  project             = var.project_id
  deletion_protection = var.proteger_tablas

  view {
    query          = templatefile("${path.module}/sql/evaluaciones.sql", local.sql_vars)
    use_legacy_sql = false
  }

  depends_on = [google_bigquery_table.tabla]
}

resource "google_bigquery_table" "hallazgos_historico" {
  dataset_id          = google_bigquery_dataset.cumplimiento.dataset_id
  table_id            = "hallazgos_historico"
  project             = var.project_id
  deletion_protection = var.proteger_tablas

  view {
    query          = templatefile("${path.module}/sql/hallazgos_historico.sql", local.sql_vars)
    use_legacy_sql = false
  }

  depends_on = [google_bigquery_table.tabla]
}

resource "google_bigquery_table" "hallazgos_abiertos" {
  dataset_id          = google_bigquery_dataset.cumplimiento.dataset_id
  table_id            = "hallazgos_abiertos"
  project             = var.project_id
  deletion_protection = var.proteger_tablas

  view {
    query          = templatefile("${path.module}/sql/hallazgos_abiertos.sql", local.sql_vars)
    use_legacy_sql = false
  }

  depends_on = [google_bigquery_table.evaluaciones, google_bigquery_table.hallazgos_historico]
}

resource "google_bigquery_table" "reporte_por_marco" {
  dataset_id          = google_bigquery_dataset.cumplimiento.dataset_id
  table_id            = "reporte_por_marco"
  project             = var.project_id
  deletion_protection = var.proteger_tablas

  view {
    query          = templatefile("${path.module}/sql/reporte_por_marco.sql", local.sql_vars)
    use_legacy_sql = false
  }

  depends_on = [google_bigquery_table.hallazgos_abiertos, google_bigquery_table.catalogo]
}

resource "google_bigquery_table" "resumen_por_marco" {
  dataset_id          = google_bigquery_dataset.cumplimiento.dataset_id
  table_id            = "resumen_por_marco"
  project             = var.project_id
  deletion_protection = var.proteger_tablas

  view {
    query          = templatefile("${path.module}/sql/resumen_por_marco.sql", local.sql_vars)
    use_legacy_sql = false
  }

  depends_on = [google_bigquery_table.reporte_por_marco]
}

locals {
  sql_vars = {
    proyecto = var.project_id
    dataset  = google_bigquery_dataset.cumplimiento.dataset_id
  }
}

# El registrador agrega filas y nada más: no puede borrar ni cambiar tablas.
resource "google_project_iam_custom_role" "registrador" {
  role_id     = "registradorEvidencia"
  project     = var.project_id
  title       = "Registrador de evidencia"
  description = "Agrega filas al índice de evidencia. Sin permiso de borrar."
  permissions = [
    "bigquery.datasets.get",
    "bigquery.tables.get",
    "bigquery.tables.updateData",
  ]
}

resource "google_bigquery_dataset_iam_member" "evidencia_agrega" {
  dataset_id = google_bigquery_dataset.cumplimiento.dataset_id
  project    = var.project_id
  role       = google_project_iam_custom_role.registrador.id
  member     = "serviceAccount:${google_service_account.evidencia.email}"
}
