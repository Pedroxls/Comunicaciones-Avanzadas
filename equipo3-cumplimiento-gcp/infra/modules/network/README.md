# Módulo de red v0.1.0

VPC de modo personalizado para dev, qa o prod. No crea la red `default` ni subredes automáticas.

Con los valores por defecto queda así:

- Subred privada con VPC Flow Logs y acceso privado a las APIs de Google.
- SSH solo desde Identity-Aware Proxy (`35.235.240.0/20`).
- HTTPS solo desde el CIDR de la subred.
- Una regla de prioridad 65534 que niega el resto de la entrada.

## Uso

```hcl
module "network" {
  source = "../../modules/network"

  project_id  = var.project_id
  region      = var.region
  name        = "dev"
  subnet_cidr = "10.10.0.0/24"
}
```

`manage_default_network` sale en `false`. En `true`, al aplicar corre `scripts/delete_default_network.sh` y borra la red `default` del proyecto si todavía existe. Hace falta `gcloud` con permiso para borrar esa red. Un plan normal no la toca.

La versión de este módulo para la semana 3 es v0.1.0. El tag git `v0.1` se pone al cerrar la semana, cuando el pipeline ya entra a GCP sin llaves.

## Prueba

```bash
terraform -chdir=infra/modules/network init -backend=false
terraform -chdir=infra/modules/network test
```
