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

Checks obligatorios en cada PR (workflow `pr-validate`): `estatico` (fmt, validate, tflint, Checkov), `politicas` (opa test), `secretos` (gitleaks) y `cumplimiento` (plan de dev evaluado con Conftest). El plan contra GCP se activa al configurar las variables `GCP_WIF_PROVIDER`, `GCP_PLAN_SA` y `GCP_PROJECT_ID` del repositorio (HU-07).

Las políticas de SSH, RDP y Telnet comparten `policies/rego/lib/firewall.rego`. El módulo `infra/modules/network` deja en dev una VPC sin subredes automáticas, con flow logs, SSH solo desde IAP (`35.235.240.0/20`) y HTTPS solo dentro de la subred. Ese plan no dispara CTL-RED-01, CTL-RED-02 ni CTL-RED-04.

## Equipo

| Integrante | Rol |
|---|---|
| Claudio Patricio Cantú Alanis | Líder de proyecto e Ingeniero IaC |
| Pedro Alejandro Rodriguez Gonzalez | Arquitecto Cloud e Ingeniero de Redes |
| Diego José Roca Rodríguez | Ingeniero de Seguridad |
| Paulo de Jesús Ibarra Carballo | Scrum Master e Ingeniero del agente |

Cómo trabajamos (ramas, commits, PR y Definition of Done): [CONTRIBUTING.md](CONTRIBUTING.md). Decisión de arquitectura: [ADR-0001](docs/adr/0001-arquitectura.md).
