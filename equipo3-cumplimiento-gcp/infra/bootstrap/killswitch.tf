# Apagado por defecto. Aunque se encienda la variable, freno.py se niega a destruir.
resource "google_cloud_run_v2_service" "freno" {
  count = var.enable_cost_killswitch ? 1 : 0

  name     = "freno-costos"
  location = var.region
  project  = var.project_id
  ingress  = "INGRESS_TRAFFIC_INTERNAL_ONLY"

  template {
    containers {
      image = var.agent_image

      env {
        name  = "KILL_ENABLED"
        value = "false"
      }
    }
  }
}
