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

variable "manage_default_network" {
  description = "Si es true, al aplicar borra la red default del proyecto y sus firewalls automáticos. Apagado por defecto: un plan normal no la toca."
  type        = bool
  default     = false
}
