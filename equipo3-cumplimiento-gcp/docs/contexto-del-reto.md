# Contexto del reto: qué nos pidieron, qué hemos hecho y qué falta

Estado al 15 de noviembre de 2026. Equipo 3, Implementación de redes de área amplia y servicios distribuidos (Gpo 503), Tecnológico de Monterrey.

Este documento reúne todo el contexto de nuestro proyecto para usarlo como insumo de la tarea **«M aparra CIS Controles benchmarks y Secure suite»** (entrega el 17 de noviembre de 2026). Se puede leer sin conocer el repositorio.

La tarea y el reto no son lo mismo:

- **La tarea** pide un plan de ciberseguridad integral para una entidad gubernamental de España que sufrió un ataque de ransomware en abril de 2023, basado en los CIS Controls y los CIS Benchmarks.
- **El reto** es nuestro proyecto del semestre: una plataforma que valida el cumplimiento de la infraestructura de Google Cloud contra el CIS Benchmark antes de desplegarla.

Lo que une a los dos es que en el reto ya aplicamos un CIS Benchmark de verdad. Las secciones 1 a 7 son el contexto del reto. La sección 8 dice qué de ese trabajo sirve para cada parte de la tarea y qué no sale de aquí.

---

## 1. Qué nos pidieron

### 1.1 El reto original

Título: «Validación de cumplimiento regulatorio con Agentic AI y Terraform».

**El problema.** Hoy el cumplimiento se revisa a mano, tarde y con evidencia dispersa. Las configuraciones inseguras se descubren hasta la auditoría, la nube se desvía del código sin que nadie lo note (drift) y la evidencia se arma a mano.

**Lo que pide.** Una plataforma de despliegue con Terraform donde un agente de IA orquesta el flujo y valida el cumplimiento antes, durante y después de cada cambio. Cinco objetivos:

1. Aprovisionar infraestructura con módulos de Terraform aprobados.
2. Validar cada plan de Terraform contra controles codificados antes de aplicarlo.
3. Vigilar el estado desplegado y detectar desviaciones.
4. Que un agente de IA orqueste la decisión, la remediación, la aprobación humana y el escalamiento.
5. Generar evidencia de auditoría trazable.

**Marcos candidatos del reto:** CNBV, LFPDPPP, PCI DSS v4.0, ISO/IEC 27001:2022, CIS Benchmarks y NIST SP 800-53 / SOC 2.

**Metas del reto:**

| Métrica | Meta |
|---|---|
| Despliegues validados por políticas antes de aplicar | 100 % |
| Tiempo de detección de drift | Menos de 1 hora |
| Tiempo de remediación de hallazgos críticos | Menos de 24 horas |
| Controles del marco prioritario codificados | 80 % en fase 2, 95 % al cierre |
| Tiempo de preparación de evidencia para auditoría | 70 % menos |
| Falsos positivos del agente | Menos de 10 % |

### 1.2 Lo que aclaró el socio formador en la primera reunión

| Tema | El reto decía | Quedó así |
|---|---|---|
| Nube | AWS, Azure y GCP | Solo GCP |
| Agente | Remedia con PR y merge automático | Alerta; no resuelve solo |
| Marcos | Seis marcos | CIS GCP como lista de verificación; el resto, mapeo documental |
| Alcance | Ciclo completo de infraestructura | Solo redes e infraestructura |
| Herramienta | Framework de agentes | Google Agent Development Kit (ADK), desplegado con Terraform |

### 1.3 Preguntas que siguen abiertas con el socio formador

| Id | Pregunta |
|---|---|
| P-01 | ¿El agente solo alerta o también sugiere la corrección? |
| P-02 | ¿Qué marcos son obligatorios además de CIS GCP? |
| P-04 | ¿Qué servicios de GCP entran en «redes e infraestructura»? |
| P-12 | ¿Cuánto tiempo se conserva la evidencia? |
| P-13 | ¿De cuántos créditos disponemos? |

---

## 2. Nuestro objetivo y la idea central

**Objetivo.** Que ningún cambio inseguro de infraestructura llegue a la nube, que cualquier cambio hecho por fuera se detecte en minutos y que la evidencia para auditoría se genere sola y no se pueda alterar.

**Idea central: el modelo explica; las políticas deciden.** El bloqueo de un despliegue inseguro no puede depender de un modelo de IA, porque un modelo se equivoca y se le puede manipular con texto. Por eso:

- Unas **políticas deterministas** (reglas escritas en Rego, evaluadas con OPA/Conftest) deciden si un cambio pasa. El mismo cambio da siempre el mismo veredicto.
- El **agente de IA** (Google ADK con Gemini) solo explica el hallazgo en lenguaje normal y avisa. No aprueba, no fusiona, no aplica y no tiene permisos sobre la infraestructura.
- Si el agente se cae, el bloqueo sigue funcionando.

**Los cinco cambios que le hicimos a la arquitectura del reto:**

| El reto proponía | Nosotros | Por qué |
|---|---|---|
| El agente decide si se aprueba o se bloquea | Las políticas bloquean solas; el agente explica aparte | Si el agente falla o alucina, el despliegue sigue protegido |
| Sensores directo al agente; drift cada hora | Un bus de eventos (Pub/Sub); aviso en minutos y revisión horaria de respaldo | No se pierden eventos |
| PR de remediación con merge automático | Sugerencia que acepta una persona | El cliente pidió alertar primero |
| Evidencia de solo anexar | Evidencia encadenada por hash en almacenamiento con retención | Un auditor comprueba que nadie la cambió |
| Sin control de costos | Presupuesto con alertas y costo estimado en cada PR | Evitar un gasto sin control |

**Cómo fluye un cambio:**

1. Alguien propone un cambio de infraestructura en un Pull Request de GitHub.
2. El pipeline genera el plan de Terraform y lo evalúa contra las políticas.
3. Si viola un control crítico o alto, el check falla y GitHub no deja fusionar.
4. El resultado se publica en el bus. El registrador lo guarda como evidencia encadenada y el agente lo explica.
5. Si alguien cambia la nube a mano, los registros de auditoría de Google lo avisan, el sensor de drift evalúa el recurso con las mismas políticas y el agente manda la alerta a Slack con quién y cuándo.

---

## 3. Equipo

| Integrante | Rol |
|---|---|
| Pedro Alejandro Rodriguez Gonzalez | Líder de proyecto, arquitecto cloud e ingeniero de redes |
| Claudio Patricio Cantú Alanis | Ingeniero de infraestructura como código |
| Diego José Roca Rodríguez | Ingeniero de Seguridad: políticas y catálogo CIS |
| Paulo de Jesús Ibarra Carballo | Scrum Master e ingeniero del agente |

El documento de diseño pone a Claudio como líder y el README a Pedro; está pendiente unificarlo. Profesores: Alejandro Parra, Rey Tapia y Luis Jorge Manzanero.

Repositorio: https://github.com/Pedroxls/Comunicaciones-Avanzadas (público).

---

## 4. Los controles del CIS Benchmark que codificamos

Usamos el **CIS Google Cloud Platform Foundation Benchmark v5.0.0**. Cada control es una política con pruebas. Los críticos y altos bloquean el cambio; los medios y bajos solo se reportan.

| Control | Qué revisa | Referencia CIS | Severidad | Bloquea |
|---|---|---|---|---|
| CTL-RED-01 | SSH (22/tcp) abierto a internet | 3.6 | Alta | Sí |
| CTL-RED-02 | RDP (3389/tcp) abierto a internet | 3.7 | Alta | Sí |
| CTL-RED-04 | Telnet (23/tcp) abierto a internet | Propio | Alta | Sí |
| CTL-RED-06 | Entrada desde internet a todos los puertos | Propio | Crítica | Sí |
| CTL-RED-03 | Existe la red `default` | 3.1 | Media | No |
| CTL-RED-05 | Subred sin registros de flujo (VPC Flow Logs) | 3.10 | Media | No |
| CTL-IAM-01 | Llave de cuenta de servicio administrada por el usuario | 1.5 | Alta | Sí |
| CTL-IAM-02 | Cuenta de servicio con rol Owner, Editor o administrador | 1.6 | Alta | Sí |
| CTL-LOG-01 | Registros de auditoría de acceso a datos sin configurar | 2.1 | Media | No |
| CTL-STO-01 | Bucket con acceso público | 5.1 | Crítica | Sí |
| CTL-ETQ-01 | Recurso sin etiquetas de dueño, ambiente, clasificación de datos, centro de costos y marco | Propio | Baja | No |
| CTL-GOB-01 | Recurso creado o cambiado fuera de Terraform (drift) | Propio | Alta | Alerta |
| CTL-GOB-02 | Recurso fuera de un módulo aprobado | Propio | Media | No |

En la v5.0.0, la recomendación 1.4 es la llave de seguridad de las cuentas de administrador. La llave de cuenta de servicio administrada por el usuario es la 1.5, y el rol de administrador en una cuenta de servicio es la 1.6.

Además corre **Checkov**, una herramienta de código abierto que trae los chequeos CIS de GCP ya hechos y revisa todo el código de Terraform.

No usamos CIS SecureSuite ni CIS-CAT. Trabajamos con el PDF gratuito del benchmark y con herramientas de código abierto (OPA, Conftest y Checkov).

---

## 5. Lo que hemos hecho, en orden

| Fecha | Qué pasó |
|---|---|
| Semana 1 | Reporte inicial: investigación, cinco riesgos y estimación PERT (134 horas con holgura) |
| 27 oct 2026 | Documento de diseño para la tercera reunión con el socio formador: arquitectura, 14 requerimientos funcionales y 12 no funcionales, backlog de 15 historias (84 puntos), wireframes, modelo de datos, APIs, plan de pruebas y 12 riesgos |
| 27 oct 2026 | Primer código: políticas de red, módulo de red seguro y workflow de validación (PR #1) |
| 28 oct 2026 | Resto del MVP en código, sin nube: bootstrap, drift, evidencia y agente (PR #2), y la lista de pendientes fuera del código (PR #3) |
| 12 nov 2026 | Auditoría completa del repositorio contra el reto y el diseño (sección 6) y corrección de todo lo que se resuelve en código |
| 15 nov 2026 | Guía de servicios externos y este documento |

Plan de construcción del MVP (50 puntos en tres semanas): Semana 3, que un PR inseguro se bloquee; Semana 4, comparar la nube real contra el código; Semana 5, que el agente explique y deje evidencia. Vamos atrasados: nada está desplegado en la nube todavía.

### Estado fino por historia

| Historia | Qué pide | En el código | Falta |
|---|---|---|---|
| HU-07 Base de GCP y costos | Proyecto con presupuesto y acceso sin llaves | Terraform completo (106 recursos): identidades sin llaves, presupuesto con alertas al 50, 90 y 100 %, estado remoto, permisos por rol | Crear el proyecto y aplicarlo |
| HU-03 Módulo de red | Red segura por defecto | Hecho y probado: sin subredes automáticas, registros de flujo, SSH solo por el proxy de identidad de Google, regla final que niega la entrada | Publicar la versión 0.1.0 |
| HU-01 Evaluar el plan en el PR | Bloquear un PR inseguro | El check evalúa el plan real del PR, incluso sin proyecto de GCP; comentario con control, severidad y recurso; workflow que aplica el mismo plan evaluado | Proteger la rama principal |
| HU-02 Catálogo | 13 controles mapeados | 13 controles, 12 políticas, 36 pruebas, y una prueba de que catálogo y políticas coinciden | Confirmar 4 referencias CIS |
| HU-04 Drift | Detectar cambios manuales | Por evento (minutos) y cada hora, con las mismas políticas | Desplegar |
| HU-05 Alertas explicadas | Alerta en lenguaje natural | Agente con Gemini y plantilla de respaldo; alerta a Slack; 30 casos etiquetados | Cuota de Vertex AI y app de Slack |
| HU-06 Evidencia inmutable | Registro encadenado | Cadena SHA-256 en almacenamiento con retención, índice en BigQuery y verificador | Desplegar |
| HU-08 Reportes | Reporte por marco | Vistas de BigQuery por marco, ambiente y control | Armar el reporte en Looker Studio |
| HU-09 a HU-13 | Aprobación humana, sugerencia de corrección, excepciones, más módulos, tablero | No construidas (posteriores al MVP) | Todo |
| HU-14, HU-15 | Merge automático, multinube | Descartadas por decisión del cliente | — |

Verificación a la fecha: 36 pruebas de políticas y 111 pruebas de Python en verde; el Terraform valida y se planea completo sin credenciales. Nada se ha probado contra Google Cloud real.

---

## 6. Lo que encontró la auditoría del 12 de noviembre

Revisamos todo el repositorio contra el reto. Esto es útil para la tarea porque es una **evaluación de controles reales**: teníamos controles escritos que no protegían nada.

| Hallazgo | Por qué importa |
|---|---|
| El gate no evaluaba el código real del PR: sin proyecto de GCP no había plan y el check pasaba | Un control que «pasa» cuando no puede evaluar no es un control |
| Con un plan real de Terraform, ninguna regla de firewall disparaba: el plan trae `disabled: null` y la política lo leía como regla apagada | Las pruebas pasaban porque usaban datos escritos a mano, no datos reales |
| Un firewall sin el campo `direction` se saltaba todas las políticas | El valor por defecto del proveedor no aparece en el plan |
| La rama principal no estaba protegida: tres PR se fusionaron con el pipeline en rojo y sin revisión | La política existía en el documento, no en la herramienta |
| El bus no tenía consumidores, la evidencia vivía en memoria y el agente nunca llamaba a Gemini | Componentes diseñados pero no conectados |
| Permisos más amplios que el diseño: cualquier PR podía asumir la cuenta que aplica cambios | Mínimo privilegio declarado, no aplicado |
| El modelo de IA configurado ya había sido retirado por Google | Dependencias externas que caducan |

Todo lo anterior ya está corregido en el código. Las lecciones: probar los controles con datos reales, hacer que un control falle cuando no puede evaluar, y no dar por aplicada una política que solo está escrita.

---

## 7. Lo que nos falta

### 7.1 Servicios y cuentas externas

Nada de esto existe hoy. El paso a paso está en [servicios-externos.md](servicios-externos.md).

| Falta | Para qué |
|---|---|
| Cuenta de Google Cloud con créditos y un proyecto | Todo el sistema vive ahí |
| Aplicar el bootstrap de Terraform | Crea identidades, bus, evidencia, BigQuery y Cloud Run |
| Seis variables en GitHub | Que el pipeline entre a GCP sin llaves |
| App de Slack y canal | Recibir las alertas |
| Comprobar la cuota de Vertex AI | Que el agente explique con Gemini |
| Reporte en Looker Studio | El reporte por marco y el PDF |
| Protección de la rama principal | Que nadie fusione sin revisión |
| Que Claudio acepte la invitación al repositorio; tablero e issues | Trabajo de los cuatro y evidencia de actividad |

### 7.2 Decisiones pendientes

1. **Seis chequeos de Checkov en rojo.** Son de cifrado con llaves propias (en BigQuery, Pub/Sub y Artifact Registry), registro de accesos en los buckets y acceso privado IPv6 en la subred. Hay que decidir entre construir un módulo de llaves (KMS) u omitirlos con justificación de Seguridad.
2. **El freno de costos no destruye nada.** Avisa, pero no borra recursos; falta definir qué es un «ambiente temporal».
3. **El candado de la retención de evidencia** queda apagado porque activarlo es irreversible.
4. **Cuatro referencias CIS por confirmar** contra la v5.0.0.
5. **Las cinco preguntas al socio formador** de la sección 1.3.

### 7.3 Lo que no está construido

Aprobación humana desde Slack y tickets (HU-09), sugerencia de corrección en el PR (HU-10), excepciones con vigencia (HU-11), módulos de almacenamiento, identidad y cifrado (HU-12), y varias rutas de consulta de la API del diseño.

### 7.4 Lo que no hemos podido comprobar

Las imágenes de los servicios (no se han construido), el `terraform apply` contra Google Cloud real, las vistas SQL dentro de BigQuery y el modelo de Gemini con una llamada real.

---

## 8. Puente con la tarea de CIS

### 8.1 Lo que pide la tarea

**Caso.** En abril de 2023 una entidad gubernamental de España sufrió un ataque de ransomware que cifró datos críticos y paralizó sus operaciones varios días. No había implementado bien los CIS Controls y no tenía plan de respuesta a incidentes.

**Preguntas guía:**

1. ¿Qué políticas y mecanismos de ciberseguridad faltaron?
2. ¿Cómo habrían mitigado el impacto los CIS Controls y benchmarks?
3. ¿Qué rol juega la legislación de ciberseguridad en la protección de datos en entidades gubernamentales?
4. ¿Qué alternativas de cifrado se podrían implementar?

**Entregable.** Un plan de ciberseguridad integral con cinco partes: evaluación de los controles actuales, mejoras basadas en CIS Controls y benchmarks, análisis de alternativas de cifrado, protocolo de respuesta a incidentes y plan de recuperación.

**Formato.** En equipo, PDF, Arial 12, interlineado 1.5, nombre «M aparra CIS». Colaboración en Google Drive, diseño en Canva y revisión cruzada entre equipos. Referencias dadas: CIS Controls v8 (PDF del curso), la página de CIS Benchmarks y el RGPD.

### 8.2 Qué de nuestro reto sirve para cada parte

| Parte de la tarea | Lo que podemos aportar desde el reto |
|---|---|
| Evaluación de controles actuales | El método que ya usamos: un catálogo con control, severidad, recurso y referencia; cada control con una prueba que pasa y una que falla. Y la sección 6 como ejemplo de evaluación honesta: controles que existían en papel y no protegían |
| Mejoras basadas en CIS Controls y benchmarks | La tabla de la sección 4: cómo una recomendación del benchmark se vuelve una regla que bloquea. Ejemplos directos contra ransomware: no exponer RDP ni SSH a internet (3.7 y 3.6), no dejar almacenamiento público (5.1), no usar llaves de larga vida (1.5), no dar roles de administrador a cuentas de servicio (1.6) |
| Alternativas de cifrado | Lo que usamos y lo que nos falta (sección 8.4) |
| Respuesta a incidentes | La parte de detección: aviso en minutos con quién, qué y cuándo; evidencia encadenada como registro forense; el principio de que el control siga funcionando si una pieza se cae (sección 8.5) |
| Plan de recuperación | Infraestructura como código (se reconstruye desde el repositorio), estado con versiones y almacenamiento con retención que no deja borrar ni sobrescribir (sección 8.5) |
| Pregunta 3, legislación | El reto parte de marcos regulatorios (CNBV, LFPDPPP, PCI DSS, ISO 27001) y de la idea de que la evidencia de cumplimiento debe ser trazable e inalterable. El contexto español de la tarea no sale de aquí |

### 8.3 Relación con los CIS Controls v8

El reto trabaja con un **Benchmark** (configuración segura de un producto). La tarea pide además los **Controls** (las 18 prácticas generales). Esta correspondencia es nuestra lectura; hay que confirmar los números y los nombres contra el PDF de CIS Controls v8 del curso.

| CIS Control v8 | Qué tiene el reto |
|---|---|
| 1. Inventario de activos | El estado de Terraform como inventario de lo desplegado; etiquetas obligatorias de dueño y ambiente |
| 3. Protección de datos | Buckets sin acceso público; etiqueta de clasificación de datos; evidencia con retención |
| 4. Configuración segura | El corazón del reto: benchmark codificado, módulo seguro por defecto y bloqueo antes de desplegar |
| 5 y 6. Cuentas y control de acceso | Sin llaves de larga vida, mínimo privilegio por cuenta, acceso por rol, sin contraseñas propias |
| 8. Registros de auditoría | Registros de auditoría de Google, registros de flujo de red y evidencia encadenada |
| 12 y 13. Red: gestión y monitoreo | Red sin reglas abiertas, sin red por defecto; detección de cambios manuales |
| 16. Seguridad del software | Revisión por Pull Request, búsqueda de secretos en el código y análisis estático |
| 17. Respuesta a incidentes | Solo la detección y el aviso. No hay plan ni roles definidos |
| 11. Recuperación de datos | Solo versiones y retención. No hay respaldos ni pruebas de restauración |

**No cubiertos por el reto**, y centrales en un caso de ransomware: gestión de vulnerabilidades y parches (7), protección de correo y navegador (9), defensa contra malware (10), concientización y capacitación (14), gestión de proveedores (15) y pruebas de penetración (18). Para la tarea, estos salen del PDF de CIS Controls, no de nuestro proyecto.

### 8.4 Cifrado: lo que usamos y lo que nos falta

| Tema | En el reto |
|---|---|
| Datos en reposo | Cifrado por defecto de Google, con llaves que administra Google |
| Llaves propias (CMEK con Cloud KMS) | No lo tenemos. Es justo lo que señalan los chequeos de Checkov pendientes |
| Datos en tránsito | HTTPS entre servicios; cada llamada lleva un token de identidad |
| Protocolos sin cifrar | Bloqueados: la política de Telnet existe porque manda credenciales en claro |
| Integridad | SHA-256 encadenado: cada registro guarda el hash del anterior, así que alterar uno rompe la cadena |
| Secretos | En un gestor de secretos; ninguno en el repositorio; un escáner revisa cada PR |
| Inmutabilidad | Almacenamiento con retención: un registro no se puede borrar ni sobrescribir antes de que venza |

Para la tarea falta lo que el reto no toca: cifrado de discos y de bases de datos, cifrado del lado del cliente, módulos de hardware (HSM), gestión y rotación de llaves, y cifrado en dispositivos móviles, que aparece en el propósito de la tarea.

### 8.5 Respuesta a incidentes y recuperación: lo que tenemos y lo que no

**Tenemos:**

- Detección en minutos de un cambio manual, con quién lo hizo y cuándo.
- Alertas con control, severidad y recurso, escritas para priorizar sin leer registros.
- Evidencia que no se puede alterar sin que se note, útil para reconstruir qué pasó.
- Comportamiento seguro ante fallas: si el agente se cae, el bloqueo sigue; si el gate no puede evaluar, el cambio no pasa.
- Infraestructura que se puede recrear desde el código.
- La idea de un procedimiento de emergencia (cambio manual que después se regulariza), anotada como riesgo R-12 pero sin procedimiento escrito.

**No tenemos:** un plan de respuesta con roles y pasos, criterios de contención, comunicación a afectados y a autoridades, respaldos fuera de línea, objetivos de tiempo de recuperación ni simulacros. En el caso de la tarea, eso es precisamente lo que faltó.

Una idea del reto que sí se traslada directo al ransomware: el almacenamiento con retención bloqueada. Si los respaldos se guardan así, un atacante que cifre o borre los sistemas no puede cifrar ni borrar los respaldos.

### 8.6 Lo que hay que traer de fuera del reto para la tarea

- El detalle de los 18 CIS Controls v8 y sus grupos de implementación (PDF del curso).
- Qué es CIS SecureSuite y qué herramientas incluye (el archivo de benchmarks y herramientas del curso).
- La legislación aplicable a una entidad pública en España: el RGPD que cita la tarea y la normativa española de seguridad del sector público.
- Los hechos del caso: qué se sabe del ataque de abril de 2023.
- Benchmarks de CIS para lo que una entidad así opera (sistemas operativos, servidores, estaciones de trabajo), que no son el de Google Cloud que nosotros usamos.
