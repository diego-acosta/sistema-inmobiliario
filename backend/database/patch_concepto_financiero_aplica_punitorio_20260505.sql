BEGIN;

ALTER TABLE public.concepto_financiero
    ADD COLUMN IF NOT EXISTS aplica_punitorio boolean NOT NULL DEFAULT false;

UPDATE public.concepto_financiero
SET aplica_punitorio = true
WHERE codigo_concepto_financiero IN (
    'CANON_LOCATIVO',
    'CUOTA_VENTA',
    'CAPITAL_VENTA',
    'SALDO_EXTRAORDINARIO'
)
  AND deleted_at IS NULL;

UPDATE public.concepto_financiero
SET aplica_punitorio = false
WHERE codigo_concepto_financiero IN (
    'PUNITORIO',
    'INTERES_MORA',
    'INTERES_FINANCIERO',
    'AJUSTE_INDEXACION',
    'CARGO_ADMINISTRATIVO',
    'EXPENSA_TRASLADADA',
    'SERVICIO_TRASLADADO',
    'IMPUESTO_TRASLADADO'
)
  AND deleted_at IS NULL;

COMMIT;
