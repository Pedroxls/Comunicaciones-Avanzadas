-- Una fila por evaluación. Un reintento de Pub/Sub puede repetir filas en la tabla.
SELECT *
FROM `${proyecto}.${dataset}.evaluacion`
QUALIFY ROW_NUMBER() OVER (PARTITION BY evaluacion_id ORDER BY registrado_en DESC) = 1
