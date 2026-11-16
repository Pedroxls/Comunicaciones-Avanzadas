# Cumplimiento regulatorio con Agentic AI y Terraform en GCP

Equipo 3 · Implementación de redes de área amplia y servicios distribuidos (Gpo 503) · Tecnológico de Monterrey

Cada cambio de infraestructura entra por Pull Request, se evalúa contra políticas de cumplimiento (CIS Google Cloud Platform Foundation Benchmark v5.0.0) y, si viola un control alto o crítico, **no se puede fusionar**. Un agente (Google ADK + Gemini en Vertex AI) explica el hallazgo y deja evidencia, pero **no decide**: el bloqueo lo pone un gate determinista con OPA/Conftest.

## Estado

El código de las ocho historias del MVP está escrito y probado sin nube. Nada está desplegado todavía: falta el proyecto de GCP. El orden de los pasos está en [docs/runbooks/puesta-en-marcha.md](docs/runbooks/puesta-en-marcha.md) y cómo se crea cada cuenta, en [docs/servicios-externos.md](docs/servicios-externos.md). El contexto completo del reto y el avance están en [docs/contexto-del-reto.md](docs/contexto-del-reto.md).

| Historia | En el código | Falta fuera del código |
|---|---|---|
| HU-07 Base de GCP y costos | Bootstrap completo: identidades sin llaves, presupuesto, estado remoto, permisos por rol | Crear el proyecto y aplicar |
| HU-03 Módulo de red | `infra/modules/network` con `terraform test` | Tag `v0.1.0` al cerrar la semana |
| HU-01 Gate en el PR | El check evalúa el plan real del PR, con o sin GCP; workflow de apply | Proteger `main` |
| HU-02 Catálogo | 13 controles, 12 políticas Rego, prueba de que catálogo y políticas coinciden | Confirmar 4 referencias CIS |
| HU-04 Drift | Por evento (Audit Logs) y cada hora (`plan -refresh-only`), con las políticas del PR | Aplicar el bootstrap |
| HU-05 Agente | ADK + Gemini con plantilla de respaldo; alerta a Slack; 30 casos | Cuota de Vertex y app de Slack |
| HU-06 Evidencia | Cadena de hashes en Cloud Storage e índice en BigQuery; verificador | Aplicar el bootstrap |
| HU-08 Reporte | Vistas de BigQuery por marco, ambiente y control | Armar el reporte en Looker Studio |

## Cómo fluye

```
PR ──► pr-validate ──► gate OPA/Conftest ──► check (bloquea o deja pasar)
                            │
                            ▼
              Pub/Sub cumplimiento-eventos ◄── drift (por evento y cada hora)
                 │                 │       ◄── freno (alertas de presupuesto)
                 ▼                 ▼
            evidencia           agente ──► Slack
        (GCS + BigQuery)           │
                 ▲                 │
                 └── decisión ◄────┘
```

Si el agente se cae, el gate sigue bloqueando y los eventos esperan en el bus. El formato de los eventos está en [docs/contrato-eventos.md](docs/contrato-eventos.md).

## Estructura

```
infra/
  bootstrap/        todo lo compartido del proyecto: identidades, presupuesto, bus, BigQuery, Cloud Run
  modules/network/  VPC segura por defecto (v0.1.0)
  environments/     dev/  qa/  prod/  (prod solo plan)
policies/
  rego/             una política por control y funciones comunes (lib/)
  tests/            un caso que pasa y uno que falla por control
  catalog/          controls.yaml, mappings.yaml, exceptions.yaml
gate/               evaluar_plan.py: corre Conftest y decide el check
comun/              contrato de eventos, bus y servidor HTTP que comparten los servicios
agent/              agente ADK: explica y avisa; evals/ con 30 casos
services/evidence/  registrador de evidencia (sin IA)
services/freno/     alertas de presupuesto
sensors/drift/      drift por evento y verificación horaria
tests/              los tres flujos de punta a punta y la consistencia del catálogo
scripts/            configuración de GitHub
docs/               ADR, contrato de eventos y runbooks
../.github/         workflows, plantillas y CODEOWNERS (GitHub solo los lee en la raíz)
```

## Probar en tu máquina

Requiere [OPA](https://www.openpolicyagent.org/docs/latest/#running-opa), [Conftest](https://www.conftest.dev/install/) 0.55, Terraform 1.9.8 y Python 3.12.

```bash
opa test policies -v                         # políticas
sh gate/fixtures/comprobar_gate.sh           # el gate bloquea Telnet y deja pasar la red base
python -m pip install pytest PyYAML
python -m pytest gate/tests tests services sensors agent/tests -q
terraform -chdir=infra/modules/network test  # módulo de red
```

Para evaluar tu cambio como lo hace el PR, sin credenciales de GCP:

```bash
cd infra/environments/dev
printf 'terraform {\n  backend "local" {}\n}\n' > backend_override.tf
terraform init -input=false
GOOGLE_OAUTH_ACCESS_TOKEN=sin-credenciales terraform plan -refresh=false -var project_id=sin-credenciales -out=tfplan
terraform show -json tfplan > plan.json
cd ../../.. && python3 gate/evaluar_plan.py && cat veredicto.md
```

## Workflows

| Workflow | Cuándo | Qué hace |
|---|---|---|
| `pr-validate` | Cada PR | `estatico` (fmt, validate, tflint, terraform test, Checkov), `politicas` (opa test y pytest), `secretos` (gitleaks), `cumplimiento` (plan + gate + comentario) e `imagenes` (las cuatro imágenes construyen y arrancan) |
| `apply-dev` | Merge a `main` | Vuelve a evaluar el plan, publica la evidencia con el sha256 del plan y aplica ese mismo archivo |
| `build-images` | Merge a `main` | Construye las imágenes y las despliega en Cloud Run |

`apply-dev` y `build-images` no hacen nada hasta que existan las variables de GCP. `MODO_POLITICAS=advertencia` reporta las violaciones sin bloquear; sin la variable el modo es `bloqueo`. Si el gate no puede evaluar, el check falla en cualquier modo.

## Equipo

| Integrante | Rol |
|---|---|
| Pedro Alejandro Rodriguez Gonzalez | Líder de proyecto, arquitecto cloud e ingeniero de redes |
| Claudio Patricio Cantú Alanis | Ingeniero IaC |
| Diego José Roca Rodríguez | Ingeniero de Seguridad |
| Paulo de Jesús Ibarra Carballo | Scrum Master e Ingeniero del agente |

Cómo trabajamos (ramas, commits, PR y Definition of Done): [CONTRIBUTING.md](CONTRIBUTING.md). Decisiones de arquitectura: [ADR-0001](docs/adr/0001-arquitectura.md) y [ADR-0002](docs/adr/0002-conexion-de-los-servicios.md). El PDF [docs/pendiente-fuera-del-codigo.pdf](docs/pendiente-fuera-del-codigo.pdf) es la foto del 28 de octubre; lo vigente es el runbook.
