mock_provider "google" {}

variables {
  project_id             = "test-project"
  region                 = "us-central1"
  name                   = "dev"
  subnet_cidr            = "10.10.0.0/24"
  manage_default_network = false
}

run "red_base_niega_la_entrada" {
  command = plan

  assert {
    condition     = google_compute_network.vpc.auto_create_subnetworks == false
    error_message = "La VPC no debe crear subredes automáticas."
  }

  assert {
    condition     = google_compute_network.vpc.name == "dev-vpc"
    error_message = "La VPC del módulo no es la red default."
  }

  assert {
    condition     = length(google_compute_subnetwork.privada.log_config) == 1
    error_message = "La subred privada debe tener flow logs."
  }

  assert {
    condition     = !contains(google_compute_firewall.iap_ssh.source_ranges, "0.0.0.0/0")
    error_message = "SSH no puede quedar abierto a internet."
  }

  assert {
    condition     = length([for regla in google_compute_firewall.denegar_entrada.deny : regla if regla.protocol == "all"]) == 1
    error_message = "Debe existir una regla que niega el resto de la entrada."
  }

  assert {
    condition     = length(terraform_data.delete_default_network) == 0
    error_message = "Con manage_default_network en false no se toca la red default."
  }
}

run "puede_borrar_la_red_default" {
  command = plan

  variables {
    manage_default_network = true
  }

  assert {
    condition     = length(terraform_data.delete_default_network) == 1
    error_message = "Con manage_default_network en true el plan incluye el borrado de la red default."
  }
}
