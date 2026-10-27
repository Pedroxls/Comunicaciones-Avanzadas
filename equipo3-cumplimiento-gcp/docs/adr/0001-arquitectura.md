# ADR-0001 · El modelo explica; las políticas deciden

- **Estado:** aceptada
- **Fecha:** 2026-10-27
- **Autores:** Equipo 3

## Contexto

El reto pide validar el cumplimiento de la infraestructura de GCP antes y después de desplegar, con un agente de IA. En la primera reunión con el socio formador quedó fijo: un solo proveedor (GCP), CIS Benchmarks para GCP como lista de verificación, solo redes e infraestructura, Google ADK desplegado con Terraform, y que el agente **alerte primero; no resuelva solo**.

Un modelo de lenguaje puede equivocarse o ser manipulado con texto dentro de los recursos (etiquetas, descripciones). Si el modelo decidiera qué se despliega, un error suyo llegaría a producción.

## Decisión

1. **Gate determinista.** El plan de Terraform de cada PR se evalúa con políticas Rego (OPA/Conftest) y chequeos de Checkov. Una violación crítica o alta bloquea el merge, esté o no disponible el agente. El mismo plan con la misma versión de políticas da siempre el mismo veredicto.
2. **El agente no está en el camino del despliegue.** El agente (Google ADK + Gemini en Vertex AI, en Cloud Run) solo lee metadatos, explica, prioriza y avisa en el PR y en Slack. Su cuenta es de solo lectura y no tiene herramientas para aplicar cambios ni fusionar.
3. **Bus de eventos.** Los resultados del gate, el drift y las alertas de presupuesto se publican en Pub/Sub con reintentos, cola de fallidos y descarte de duplicados por `evento_id`.
4. **Drift con las mismas políticas.** Un job de Cloud Run corre `terraform plan -refresh-only` cuando Audit Logs registra un cambio manual y, como respaldo, cada hora; evalúa el resultado con el mismo catálogo.
5. **Evidencia encadenada.** Un registrador sin IA guarda cada evaluación y decisión en GCS con retención bloqueada e índice en BigQuery; cada registro incluye el hash del anterior. En dev la retención es de 1 día porque bloquearla es irreversible.
6. **Freno de costos.** Presupuesto con alertas al 50, 90 y 100 % y un freno que destruye los ambientes temporales; Infracost estima el costo de cada PR.

## Consecuencias

- Si el agente falla, el control sigue funcionando; solo falta la explicación ("explicación pendiente" en el PR).
- La corrección que proponga el agente es una sugerencia dentro del mismo PR que solo una persona puede aplicar (HU-10, después del MVP).
- No construimos una aplicación nueva: el resultado vive en el PR, en Slack y en un reporte de Looker Studio sobre BigQuery.
- Más piezas que operar (Pub/Sub, job de drift, registrador). Se mitiga con servicios que escalan a cero y con el freno de costos.

## Alternativas descartadas

| Alternativa | Por qué no |
|---|---|
| Que el agente decida si se aprueba el PR | No es determinista y se puede manipular con texto en los recursos |
| Remediación automática del agente | La primera reunión pidió alertar primero, no resolver solo |
| Llamadas directas entre servicios sin bus | Un servicio caído perdería eventos |
| Una política distinta para el drift | Dos conjuntos de reglas acabarían diciendo cosas diferentes |
