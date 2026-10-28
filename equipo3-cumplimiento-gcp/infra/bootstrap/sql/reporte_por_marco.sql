SELECT
  marco_id,
  ambiente,
  control_id,
  COUNTIF(estado = "abierto") AS abiertos,
  COUNT(*) AS hallazgos
FROM `${proyecto}.${dataset}.hallazgo`
GROUP BY marco_id, ambiente, control_id
