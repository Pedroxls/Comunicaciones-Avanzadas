resource "google_compute_firewall" "demo_telnet" {
  project       = var.project_id
  name          = "dev-demo-https-interna"
  network       = module.network.network_name
  direction     = "INGRESS"
  source_ranges = ["10.10.0.0/24"]

  allow {
    protocol = "tcp"
    ports    = ["443"]
  }
}
