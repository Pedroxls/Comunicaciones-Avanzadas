## Historia

<!-- Ejemplo: HU-01 Evaluar el plan en el PR. Enlaza el issue: Closes #12 -->
HU-

## Qué cambia

-

## Controles afectados

<!-- Ids del catálogo (policies/catalog/controls.yaml). Escribe "ninguno" si no aplica. -->
- CTL-

## Ambiente

- [ ] dev
- [ ] qa
- [ ] prod (solo plan)

## Evidencia

<!-- Pega el resumen del plan, el costo de Infracost y el enlace al check de cumplimiento. -->
- Plan:
- Costo estimado:
- Check de cumplimiento:

## Definition of Done

- [ ] Los criterios de aceptación de la historia se cumplen
- [ ] Los checks están en verde (fmt, validate, tflint, Checkov, opa test, gitleaks)
- [ ] Si agregué o cambié una política, tiene un caso que pasa y uno que falla
- [ ] No hay secretos, `.tfstate` ni `.tfvars` reales en el PR
- [ ] No quedan recursos de prueba encendidos en GCP
