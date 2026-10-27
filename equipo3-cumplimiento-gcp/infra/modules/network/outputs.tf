output "network_name" {
  description = "Nombre de la VPC."
  value       = google_compute_network.vpc.name
}

output "network_id" {
  description = "Id de la VPC."
  value       = google_compute_network.vpc.id
}

output "subnet_name" {
  description = "Nombre de la subred privada."
  value       = google_compute_subnetwork.privada.name
}

output "subnet_cidr" {
  description = "CIDR de la subred privada."
  value       = google_compute_subnetwork.privada.ip_cidr_range
}
