-- Una fila por marco, ambiente y control: cumple o no cumple hoy.
-- Los controles sin mapeo salen bajo el marco PROPIO.
WITH ambientes AS (
  SELECT DISTINCT ambiente FROM `${proyecto}.${dataset}.evaluaciones`
  UNION DISTINCT
  SELECT 'dev' AS ambiente
),
controles AS (
  SELECT
    c.control_id,
    c.titulo,
    c.severidad,
    c.bloquea,
    COALESCE(m.marco_id, 'PROPIO') AS marco_id,
    COALESCE(m.requisito, 'Control propio') AS requisito
  FROM `${proyecto}.${dataset}.catalogo_control` AS c
  LEFT JOIN `${proyecto}.${dataset}.catalogo_marco` AS m
    ON m.control_id = c.control_id
)
SELECT
  c.marco_id,
  a.ambiente,
  c.control_id,
  c.titulo,
  c.requisito,
  c.severidad,
  c.bloquea,
  COUNT(h.hallazgo_id) AS hallazgos_abiertos,
  CASE WHEN COUNT(h.hallazgo_id) = 0 THEN 'cumple' ELSE 'no cumple' END AS estado,
  MAX(h.detectado_en) AS ultimo_hallazgo,
  MAX_BY(h.evidencia_id, h.detectado_en) AS ultima_evidencia
FROM controles AS c
CROSS JOIN ambientes AS a
LEFT JOIN `${proyecto}.${dataset}.hallazgos_abiertos` AS h
  ON h.control_id = c.control_id AND h.ambiente = a.ambiente
GROUP BY c.marco_id, a.ambiente, c.control_id, c.titulo, c.requisito, c.severidad, c.bloquea
