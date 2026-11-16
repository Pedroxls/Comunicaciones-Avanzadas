-- Lo que hoy incumple cada ambiente.
--
-- Un hallazgo de PR no cuenta: si bloqueó, el cambio nunca llegó a la nube.
-- Cuentan los de lo aplicado (origen apply) y los de drift. Un hallazgo sigue
-- abierto mientras lo vea la última evaluación completa de su origen, o si un
-- aviso por evento lo detectó después de esa evaluación.
WITH ultima_completa AS (
  SELECT ambiente, origen, evaluacion_id, ocurrido_en
  FROM `${proyecto}.${dataset}.evaluaciones`
  WHERE alcance = 'completo' AND origen IN ('apply', 'drift')
  QUALIFY ROW_NUMBER() OVER (PARTITION BY ambiente, origen ORDER BY ocurrido_en DESC) = 1
)
SELECT
  h.hallazgo_id,
  h.control_id,
  h.severidad,
  h.bloquea,
  h.recurso,
  h.detalle,
  h.actor,
  h.ambiente,
  h.origen,
  h.detectado_en,
  h.evidencia_id
FROM `${proyecto}.${dataset}.hallazgos_historico` AS h
LEFT JOIN ultima_completa AS u
  ON u.ambiente = h.ambiente AND u.origen = h.origen
WHERE h.origen IN ('apply', 'drift')
  AND h.estado = 'abierto'
  AND (
    u.evaluacion_id IS NULL
    OR h.evaluacion_id = u.evaluacion_id
    OR (h.origen = 'drift' AND h.detectado_en > u.ocurrido_en)
  )
QUALIFY ROW_NUMBER() OVER (PARTITION BY h.hallazgo_id ORDER BY h.detectado_en DESC) = 1
