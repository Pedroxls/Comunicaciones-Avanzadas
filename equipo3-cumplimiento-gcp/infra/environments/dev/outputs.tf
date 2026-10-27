output "network_name" {
  description = "VPC de dev."
  value       = module.network.network_name
}

output "subnet_cidr" {
  description = "CIDR de la subred privada de dev."
  value       = module.network.subnet_cidr
}
