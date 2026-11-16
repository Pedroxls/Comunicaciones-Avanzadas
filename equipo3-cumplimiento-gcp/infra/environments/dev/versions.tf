# Versiones fijas del ambiente dev.
#
# El estado vive en el bucket que crea infra/bootstrap. El bucket y el prefijo
# se pasan al inicializar, para no escribir el proyecto en el repositorio:
#
#   terraform init -backend-config="bucket=<proyecto>-tfstate" -backend-config="prefix=environments/dev"
#
# El check de cumplimiento del PR también planea sin credenciales de GCP; para
# eso el workflow agrega un backend local con un archivo backend_override.tf.
terraform {
  required_version = "~> 1.9.0"

  backend "gcs" {}

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
  }
}
