provider "google" {
  project = var.project_id
  region  = var.region
}

# La API de presupuestos rechaza las credenciales de usuario (gcloud auth
# application-default login) si la llamada no lleva un proyecto de cuota.
# Solo el presupuesto usa este provider.
provider "google" {
  alias                 = "facturacion"
  project               = var.project_id
  region                = var.region
  billing_project       = var.project_id
  user_project_override = true
}
