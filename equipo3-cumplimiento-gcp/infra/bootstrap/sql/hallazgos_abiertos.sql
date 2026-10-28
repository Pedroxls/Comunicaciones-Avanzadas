SELECT
  hallazgo_id,
  control_id,
  marco_id,
  ambiente,
  severidad,
  self_link,
  actor,
  detectado_en,
  evidencia_id
FROM `${proyecto}.${dataset}.hallazgo`
WHERE estado = "abierto"
