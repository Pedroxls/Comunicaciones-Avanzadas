variable "project_id" {
  description = "Proyecto de GCP donde se crea la red."
  type        = string

  validation {
    condition     = length(var.project_id) > 0
    error_message = "Define project_id."
  }
}

variable "region" {
  description = "Región de la subred."
  type        = string
}

variable "name" {
  description = "Prefijo de los recursos. En dev se usa el nombre del ambiente."
  type        = string
}

variable "subnet_cidr" {
  description = "CIDR de la subred privada."
  type        = string
}
