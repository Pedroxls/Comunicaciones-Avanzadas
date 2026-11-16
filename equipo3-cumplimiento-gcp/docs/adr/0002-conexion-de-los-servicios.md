# ADR-0002 · Cómo se conectan el gate, el bus y los servicios

- **Estado:** propuesta
- **Fecha:** 2026-11-12
- **Autores:** Equipo 3

## Contexto

El ADR-0001 fijó qué piezas hay. Al conectarlas aparecieron cinco puntos donde el diseño no decía cómo, o donde lo que decía no funciona con un plan real de Terraform.

## Decisión

1. **El gate planea aunque no haya proyecto de GCP.** Sin las variables de GitHub, el check `cumplimiento` genera el plan con un estado local vacío y un token sin valor. Evalúa todo `infra/environments/dev` como si se creara desde cero. Con las variables, planea contra el estado real. En ningún caso el check pasa sin haber evaluado un plan.

2. **Las políticas tratan lo que el plan no conoce como el peor caso.** En un plan real, un firewall sin `direction` no trae el campo (GCP usa INGRESS), `disabled` sin escribir llega como `null` y un rango calculado no se conoce hasta aplicar. Las políticas evalúan los tres casos como regla de entrada, activa y abierta a internet. Los fixtures del gate ahora salen de `terraform show -json`, no escritos a mano.

3. **El drift por evento evalúa el recurso como quedó, no el registro.** El registro de Audit Logs de un `patch` solo trae los campos que cambiaron. El sensor toma de ahí quién y cuándo, lee el recurso de la API de Compute y lo evalúa con las políticas del PR. Así también detecta una regla nueva creada en la consola, que `terraform plan` no ve porque no está en el estado. La verificación horaria con `plan -refresh-only` queda de respaldo y es la que cierra los hallazgos corregidos.

4. **La cadena de evidencia usa el nombre del objeto como candado.** Cada registro es `cadena/<secuencia>.json` y se crea solo si no existe. Dos instancias no pueden escribir la misma posición; la que pierde vuelve a leer el último registro y reintenta. No hace falta un objeto «cabeza» que habría que sobrescribir, cosa que la retención del bucket impide.

5. **Al modelo no le llegan las etiquetas ni texto libre del recurso.** Recibe el control, la severidad, la dirección del recurso, el detalle que escribió la política, el ambiente y el veredicto. Si su respuesta no cita el control o se alarga, responde la plantilla. El mensaje de Slack arma el control, el recurso, quién y cuándo desde el evento, no desde el modelo.

6. **Aplicar y desplegar solo desde `main`.** Las cuentas `apply-dev` y `despliegue` solo se pueden asumir con un token de GitHub cuya rama sea `refs/heads/main`. La cuenta `plan-pr`, que usa cualquier PR, es de solo lectura.

## Consecuencias

- Un PR que abre Telnet se bloquea hoy, antes de tener el proyecto de GCP.
- El agente ya no tiene permisos de lectura sobre la infraestructura: solo llama a Gemini, publica su decisión y lee el token de Slack. La lectura de la nube la hace el sensor de drift.
- El reporte distingue lo que se bloqueó en un PR (nunca llegó a la nube) de lo que hoy incumple un ambiente (lo aplicado y el drift). Solo lo segundo cuenta como control incumplido.
- El agente puede repetir una alerta si se reinicia entre dos avisos iguales: recuerda los eventos vistos en memoria. La evidencia no se duplica.

## Lo que queda fuera

- Rutas de la API del diseño que no se construyeron: consulta y cambio de estado de hallazgos, acciones de Slack, tickets y excepciones. El reporte lee BigQuery directo; las demás son de HU-09 a HU-11.
- `exceptions.yaml` sigue sin leerse desde las políticas (HU-11).
- El freno avisa pero no destruye recursos.
