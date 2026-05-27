-- patch_plan_pago_venta_bloque_metodo_liquidacion_20260527.sql
-- Soporte fisico minimo para metodo_liquidacion por bloque/tramo en Plan Pago V2.
--
-- Alcance:
-- - Extiende plan_pago_venta_bloque con columnas opcionales para liquidacion por bloque.
-- - No altera metodo_plan_pago global en plan_pago_venta.
-- - Mantiene compatibilidad legacy: TRAMO_CUOTAS puede permanecer sin metodo_liquidacion.

ALTER TABLE public.plan_pago_venta_bloque
    ADD COLUMN IF NOT EXISTS metodo_liquidacion VARCHAR(40) NULL,
    ADD COLUMN IF NOT EXISTS tasa_interes_directo_periodica NUMERIC(12,8) NULL,
    ADD COLUMN IF NOT EXISTS cantidad_periodos INTEGER NULL,
    ADD COLUMN IF NOT EXISTS base_calculo_interes VARCHAR(40) NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'chk_ppvb_metodo_liquidacion'
          AND conrelid = 'public.plan_pago_venta_bloque'::regclass
    ) THEN
        ALTER TABLE public.plan_pago_venta_bloque
        ADD CONSTRAINT chk_ppvb_metodo_liquidacion
        CHECK (
            metodo_liquidacion IS NULL
            OR metodo_liquidacion IN ('SIN_INTERES', 'INTERES_DIRECTO')
        );
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'chk_ppvb_tasa_interes_directo_periodica'
          AND conrelid = 'public.plan_pago_venta_bloque'::regclass
    ) THEN
        ALTER TABLE public.plan_pago_venta_bloque
        ADD CONSTRAINT chk_ppvb_tasa_interes_directo_periodica
        CHECK (
            tasa_interes_directo_periodica IS NULL
            OR tasa_interes_directo_periodica >= 0
        );
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'chk_ppvb_cantidad_periodos'
          AND conrelid = 'public.plan_pago_venta_bloque'::regclass
    ) THEN
        ALTER TABLE public.plan_pago_venta_bloque
        ADD CONSTRAINT chk_ppvb_cantidad_periodos
        CHECK (
            cantidad_periodos IS NULL
            OR cantidad_periodos > 0
        );
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'chk_ppvb_base_calculo_interes'
          AND conrelid = 'public.plan_pago_venta_bloque'::regclass
    ) THEN
        ALTER TABLE public.plan_pago_venta_bloque
        ADD CONSTRAINT chk_ppvb_base_calculo_interes
        CHECK (
            base_calculo_interes IS NULL
            OR base_calculo_interes IN ('CAPITAL_INICIAL_BLOQUE')
        );
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'chk_ppvb_interes_directo_tramo_cuotas'
          AND conrelid = 'public.plan_pago_venta_bloque'::regclass
    ) THEN
        ALTER TABLE public.plan_pago_venta_bloque
        ADD CONSTRAINT chk_ppvb_interes_directo_tramo_cuotas
        CHECK (
            metodo_liquidacion IS DISTINCT FROM 'INTERES_DIRECTO'
            OR (
                tipo_bloque = 'TRAMO_CUOTAS'
                AND tasa_interes_directo_periodica IS NOT NULL
                AND cantidad_periodos IS NOT NULL
                AND base_calculo_interes IS NOT NULL
            )
        );
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_plan_pago_venta_bloque_metodo_liquidacion
ON public.plan_pago_venta_bloque (metodo_liquidacion);
