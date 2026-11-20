resource "google_compute_firewall" "demo_telnet" {
  project       = var.project_id
  name          = "dev-demo-telnet"
  network       = module.network.network_name
  direction     = "INGRESS"
  source_ranges = ["0.0.0.0/0"]

  allow {
    protocol = "tcp"
    ports    = ["23"]
  }
}
