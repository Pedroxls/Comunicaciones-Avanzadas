-- Todo lo que se ha encontrado, de cualquier origen. Para consultar por periodo
-- y para la página de evaluaciones de PR.
SELECT *
FROM `${proyecto}.${dataset}.hallazgo`
QUALIFY ROW_NUMBER() OVER (PARTITION BY hallazgo_id, evaluacion_id ORDER BY registrado_en DESC) = 1
