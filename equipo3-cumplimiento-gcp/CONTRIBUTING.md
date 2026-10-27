# Cómo contribuir

## Ramas (trunk-based)

`main` siempre pasa los checks y siempre se puede demostrar. Nadie hace push directo: todo entra por PR.

| Rama | Para qué | Regla |
|---|---|---|
| `feat/HU-xx-nombre` | Una historia de usuario | Dura 3 días o menos |
| `policy/CTL-xx-nombre` | Política nueva o cambio en un control | La aprueba Seguridad (CODEOWNERS) |
| `fix/descripcion` | Corrección de un error | Mismos checks y revisión |
| `tag v0.N` | Cierre de cada semana (v0.1 = Semana 3) | Se promueve a qa por carpeta, no por rama |

La rama es **por historia, no por persona**. `dev`, `qa` y `prod` son carpetas en `infra/environments/`, no ramas. No usamos GitFlow.

## Commits

Formato: `tipo(HU-xx): descripción en minúsculas`

- `feat(HU-01): política de telnet abierto a internet`
- `test(HU-01): caso de rango de puertos que incluye ssh`
- `fix(HU-03): flow logs en la subred privada`
- `docs: adr-0001 de la arquitectura`
- `chore: versiones fijas de terraform`

Tipos: `feat`, `fix`, `test`, `docs`, `chore`, `ci`, `refactor`.

## Pull Requests

1. Sale de `main` y regresa a `main`.
2. Llena la plantilla: historia, controles afectados, ambiente y evidencia.
3. Necesita **1 aprobación de otra persona** y todos los checks en verde.
4. Se fusiona con **squash**; GitHub borra la rama al fusionar.
5. Los cambios en `policies/` los aprueba Seguridad.

## Políticas

- Una política por control, con el id del catálogo en el mensaje: `[CTL-RED-04][alta] recurso: detalle`.
- `deny` bloquea el merge (crítica y alta); `warn` solo reporta (media y baja).
- Cada política tiene **al menos un caso que pasa y uno que falla** en `policies/tests/`.
- Todo control nuevo se agrega primero en `policies/catalog/controls.yaml` y su mapeo en `mappings.yaml`.

## Definition of Done

- Criterios de aceptación de la historia cumplidos y sus casos de prueba pasan.
- `terraform fmt`, `validate`, `tflint`, Checkov, `opa test` y gitleaks en verde.
- La validación del PR tarda 5 minutos o menos.
- Sin recursos de prueba encendidos en GCP al terminar.
- README o ADR actualizado si cambió una decisión.

## Lo que nunca va al repositorio

Llaves de cuentas de servicio, tokens, archivos `.tfstate`, `.tfvars` con datos reales ni planes (`tfplan`, `plan.json`). Los secretos viven en Secret Manager y en los secretos de GitHub.
