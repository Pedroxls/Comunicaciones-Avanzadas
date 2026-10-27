# Versiones fijas del ambiente dev. El backend remoto (bucket de GCS con versionado)
# se agrega en HU-07, cuando exista el bucket creado por infra/bootstrap.
terraform {
  required_version = "~> 1.9.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
  }
}
