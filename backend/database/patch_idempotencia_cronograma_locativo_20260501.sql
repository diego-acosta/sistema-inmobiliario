-- patch_idempotencia_cronograma_locativo_20260501.sql
-- Idempotencia SQL fuerte para cronograma locativo-financiero.
-- Las consultas diagnostico deben devolver cero filas antes de crear indices.

-- Diagnostico: relaciones generadoras activas duplicadas por origen.
SELECT
    tipo_origen,
    id_origen,
    COUNT(*) AS cantidad
FROM public.relacion_generadora
WHERE deleted_at IS NULL
GROUP BY tipo_origen, id_origen
HAVING COUNT(*) > 1;

-- Diagnostico: obligaciones activas duplicadas por relacion y periodo.
SELECT
    id_relacion_generadora,
    periodo_desde,
    periodo_hasta,
    COUNT(*) AS cantidad
FROM public.obligacion_financiera
WHERE deleted_at IS NULL
  AND periodo_desde IS NOT NULL
  AND periodo_hasta IS NOT NULL
GROUP BY id_relacion_generadora, periodo_desde, periodo_hasta
HAVING COUNT(*) > 1;

CREATE UNIQUE INDEX IF NOT EXISTS uq_relacion_generadora_origen_activo
    ON public.relacion_generadora (tipo_origen, id_origen)
    WHERE deleted_at IS NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_obligacion_financiera_cronograma_periodo_activo
    ON public.obligacion_financiera (id_relacion_generadora, periodo_desde, periodo_hasta)
    WHERE deleted_at IS NULL;
