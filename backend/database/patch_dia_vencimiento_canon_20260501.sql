-- patch_dia_vencimiento_canon_20260501.sql
-- Agrega dia_vencimiento_canon a contrato_alquiler.
-- Determina el día del mes en que vence el canon locativo.
-- NULL significa que se usa periodo_desde como fallback técnico.

ALTER TABLE public.contrato_alquiler
    ADD COLUMN IF NOT EXISTS dia_vencimiento_canon integer;

ALTER TABLE public.contrato_alquiler
    DROP CONSTRAINT IF EXISTS chk_dia_vencimiento_canon;

ALTER TABLE public.contrato_alquiler
    ADD CONSTRAINT chk_dia_vencimiento_canon
    CHECK ((dia_vencimiento_canon IS NULL) OR (dia_vencimiento_canon BETWEEN 1 AND 31));
