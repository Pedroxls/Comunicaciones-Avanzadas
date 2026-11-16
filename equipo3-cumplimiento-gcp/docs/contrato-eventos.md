# Contrato de eventos del bus

Todo lo que pasa se publica como un mensaje JSON en el tema de Pub/Sub `cumplimiento-eventos`. El código que arma y valida el evento es uno solo: [`comun/eventos.py`](../comun/eventos.py). Si cambia este contrato, cambia ese archivo y sus pruebas.

## Quién publica y quién recibe

| Tipo | Lo publica | Lo recibe |
|---|---|---|
| `gate.resultado` | El pipeline, en cada PR (`origen: pr`) y antes de cada apply (`origen: apply`) | Evidencia |
| `drift` | El sensor de drift: por cada cambio manual (`alcance: recurso`) y en la verificación horaria (`alcance: completo`) | Evidencia y agente |
| `presupuesto` | El freno de costos, cuando el gasto cruza 50, 90 o 100 % | Evidencia y agente |
| `agente.decision` | El agente, por cada evento que explica | Evidencia |

El mensaje lleva el atributo `tipo`. La suscripción del agente filtra por ese atributo: solo recibe `drift` y `presupuesto`. El resultado de un PR se explica en el PR (el pipeline le pide la explicación al agente por HTTP), y el agente no recibe sus propias decisiones.

Dos temas más llevan mensajes crudos, que un servicio convierte a este contrato:

- `auditoria-cambios`: registros de Cloud Audit Logs. Los lee el sensor de drift.
- `presupuesto-alertas`: avisos de Cloud Billing. Los lee el freno de costos.

## Campos

| Campo | Obligatorio | Contenido |
|---|---|---|
| `evento_id` | sí | Identificador único. Un evento repetido con el mismo id no genera evidencia nueva |
| `tipo` | sí | `gate.resultado`, `drift`, `presupuesto` o `agente.decision` |
| `veredicto` | sí | `aprobado`, `bloqueado`, `con_advertencias` o `alerta`. Lo dan las políticas; el agente lo copia, no lo cambia |
| `ambiente` | sí | `dev`, `qa` o `prod` |
| `ocurrido_en` | sí | Fecha y hora en ISO 8601 |
| `hallazgos` | sí | Lista, puede ir vacía. Cada uno: `control_id`, `severidad`, `recurso`, `detalle` y `bloquea` |
| `origen` | en evaluaciones | `pr`, `apply` o `drift` |
| `alcance` | en evaluaciones | `completo` (todo el ambiente) o `recurso` (un cambio manual) |
| `actor` | si se conoce | Quién hizo el cambio |
| `commit_sha`, `pr_numero`, `modo`, `duracion_seg` | en `gate.resultado` | Datos del PR y de la corrida |
| `plan_sha256` | en `origen: apply` | Hash del archivo de plan que se aplicó |
| `porcentaje`, `costo`, `presupuesto`, `moneda`, `freno` | en `presupuesto` | Datos del aviso de Cloud Billing |
| `evento_origen_id`, `razonamiento`, `herramientas`, `accion`, `fuente`, `modelo` | en `agente.decision` | Qué evento explicó, qué dijo, con qué herramientas, por dónde avisó y si respondió Gemini (`vertex`) o la plantilla |

## Ejemplo

```json
{
  "evento_id": "3f0c6c0e-6f2b-4a57-9a3e-0f8a1f6d2b11",
  "tipo": "gate.resultado",
  "veredicto": "bloqueado",
  "ambiente": "dev",
  "ocurrido_en": "2026-11-12T15:02:00+00:00",
  "origen": "pr",
  "alcance": "completo",
  "modo": "bloqueo",
  "pr_numero": 14,
  "commit_sha": "abc1234def",
  "duracion_seg": 2.4,
  "hallazgos": [
    {
      "control_id": "CTL-RED-04",
      "severidad": "alta",
      "recurso": "google_compute_firewall.telnet",
      "detalle": "Telnet (23/tcp) abierto a 0.0.0.0/0; envía credenciales sin cifrar",
      "bloquea": true
    }
  ]
}
```

## Errores

Un servicio que recibe un evento que no cumple el contrato responde 400. Pub/Sub lo reintenta cinco veces y después lo deja en `cumplimiento-eventos-fallidos`, donde se conserva siete días. Un error temporal (BigQuery, Slack o Vertex no responden) devuelve 503 y sigue el mismo camino.
