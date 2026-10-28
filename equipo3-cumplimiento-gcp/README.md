# Cumplimiento regulatorio con Agentic AI y Terraform en GCP

Equipo 3 · Implementación de redes de área amplia y servicios distribuidos (Gpo 503) · Tecnológico de Monterrey

Cada cambio de infraestructura entra por Pull Request, se evalúa contra políticas de cumplimiento (CIS Google Cloud Platform Foundation Benchmark v5.0.0) y, si viola un control alto o crítico, **no se puede fusionar**. Un agente (Google ADK + Gemini en Vertex AI) explica el hallazgo y deja evidencia, pero **no decide**: el bloqueo lo pone un gate determinista con OPA/Conftest.

## Estado

| Semana | Meta | Historias | Estado |
|---|---|---|---|
| 3 | Que un PR inseguro se bloquee en GCP | HU-07, HU-03, HU-01 (16 pts) | En curso |
| 4 | Comparar la nube real contra el código | HU-02, HU-04 (16 pts) | Pendiente |
| 5 | Que el agente explique y deje evidencia | HU-05, HU-06, HU-08 (18 pts) | Pendiente |

## Estructura

```
infra/
  bootstrap/        estado remoto, Workload Identity Federation, presupuesto, grupos de IAM
  modules/          network, logging, evidence, agent
  environments/     dev/  qa/  prod/  (prod solo plan)
policies/
  rego/             una política por control (un paquete por control) y funciones comunes (lib/)
  tests/            un caso que pasa y uno que falla por control
  catalog/          controls.yaml, mappings.yaml, exceptions.yaml
agent/              servicio ADK: herramientas y prompts
  evals/            30 casos etiquetados
services/evidence/  registrador de evidencia (sin IA)
sensors/drift/      job de verificación de drift
../.github/         workflow pr-validate, plantillas de PR e issues, CODEOWNERS (GitHub solo los lee en la raíz del repo)
docs/adr/           decisiones de arquitectura
```

## Probar las políticas en tu máquina

Requiere [OPA](https://www.openpolicyagent.org/docs/latest/#running-opa) 0.59 o más reciente.

```bash
opa test policies/ -v          # pruebas de las políticas
opa fmt --list policies/       # no debe listar archivos
```

Para evaluar un plan real (cuando exista `infra/environments/dev`):

```bash
cd infra/environments/dev
terraform init && terraform plan -out tfplan && terraform show -json tfplan > plan.json
conftest test plan.json --policy ../../../policies/rego --all-namespaces
```

Checks obligatorios en cada PR (workflow `pr-validate`): `estatico` (fmt, validate, tflint, terraform test, Checkov), `politicas` (opa test y pytest), `secretos` (gitleaks) y `cumplimiento`. El cumplimiento siempre demuestra que un plan con Telnet a `0.0.0.0/0` produce `CTL-RED-04` y que la red base no tiene `deny`. El plan contra GCP se suma al configurar `GCP_WIF_PROVIDER`, `GCP_PLAN_SA` y `GCP_PROJECT_ID` (HU-07). `MODO_POLITICAS=advertencia` reporta las violaciones del plan real sin bloquear; en el curso el valor es `bloqueo`. Si no hay `AGENTE_URL`, el comentario del PR dice «explicación pendiente».

Las políticas comparten `policies/rego/lib/`. El módulo `infra/modules/network` (v0.1.0) deja en dev una VPC sin subredes automáticas, con flow logs, SSH solo desde IAP (`35.235.240.0/20`), HTTPS solo dentro de la subred y una regla que niega el resto de la entrada. Ese plan no dispara los controles que bloquean.

Lo que hay que crear en consolas (proyecto, billing, Slack, Looker y las variables de GitHub) está en [docs/pendiente-fuera-del-codigo.pdf](docs/pendiente-fuera-del-codigo.pdf).

## Equipo

| Integrante | Rol |
|---|---|
| Pedro Alejandro Rodriguez Gonzalez | Líder de proyecto, arquitecto cloud e ingeniero de redes |
| Claudio Patricio Cantú Alanis | Ingeniero IaC |
| Diego José Roca Rodríguez | Ingeniero de Seguridad |
| Paulo de Jesús Ibarra Carballo | Scrum Master e Ingeniero del agente |

Cómo trabajamos (ramas, commits, PR y Definition of Done): [CONTRIBUTING.md](CONTRIBUTING.md). Decisión de arquitectura: [ADR-0001](docs/adr/0001-arquitectura.md).
