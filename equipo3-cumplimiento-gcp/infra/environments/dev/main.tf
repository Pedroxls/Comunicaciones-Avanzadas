provider "google" {
  project = var.project_id
  region  = var.region
}

module "network" {
  source = "../../modules/network"

  project_id  = var.project_id
  region      = var.region
  name        = "dev"
  subnet_cidr = "10.10.0.0/24"
}
