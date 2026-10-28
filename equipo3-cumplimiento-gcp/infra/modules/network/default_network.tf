# La red default la crea GCP en el proyecto, no este módulo. Borrarla exige
# quitar antes sus firewalls automáticos. Solo corre si manage_default_network
# es true, para que un plan normal no toque el proyecto.
resource "terraform_data" "delete_default_network" {
  count = var.manage_default_network ? 1 : 0

  input = var.project_id

  provisioner "local-exec" {
    command = "${path.module}/scripts/delete_default_network.sh ${var.project_id}"
  }
}
