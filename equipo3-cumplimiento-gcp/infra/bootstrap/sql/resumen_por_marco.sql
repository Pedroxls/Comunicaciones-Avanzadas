-- Encabezado del reporte: «10 de 12 controles cumplen (83 %)».
SELECT
  marco_id,
  ambiente,
  COUNT(*) AS controles,
  COUNTIF(estado = 'cumple') AS controles_que_cumplen,
  ROUND(100 * COUNTIF(estado = 'cumple') / COUNT(*), 1) AS porcentaje_cumplimiento,
  SUM(hallazgos_abiertos) AS hallazgos_abiertos
FROM `${proyecto}.${dataset}.reporte_por_marco`
GROUP BY marco_id, ambiente
