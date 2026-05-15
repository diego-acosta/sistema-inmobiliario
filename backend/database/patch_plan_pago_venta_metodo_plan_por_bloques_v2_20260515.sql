-- Patch V2: metodo formal para planes de pago estructurados por bloques.
-- PLAN_POR_BLOQUES identifica el motor comercial basado en
-- plan_pago_venta_bloque. CRONOGRAMA_DEFINIDO queda reservado para cronogramas
-- manuales/libres.

DO $$
DECLARE
    v_definition text;
BEGIN
    SELECT pg_get_constraintdef(oid)
      INTO v_definition
    FROM pg_constraint
    WHERE conname = 'chk_plan_pago_venta_metodo'
      AND conrelid = 'public.plan_pago_venta'::regclass;

    IF v_definition IS NULL THEN
        ALTER TABLE public.plan_pago_venta
            ADD CONSTRAINT chk_plan_pago_venta_metodo
            CHECK (metodo_plan_pago IN (
                'CUOTAS_IGUALES_SIMPLE',
                'ANTICIPO_MAS_CUOTAS_IGUALES',
                'CRONOGRAMA_DEFINIDO',
                'PLAN_POR_BLOQUES'
            ));
    ELSIF v_definition NOT LIKE '%PLAN_POR_BLOQUES%' THEN
        ALTER TABLE public.plan_pago_venta
            DROP CONSTRAINT chk_plan_pago_venta_metodo;

        ALTER TABLE public.plan_pago_venta
            ADD CONSTRAINT chk_plan_pago_venta_metodo
            CHECK (metodo_plan_pago IN (
                'CUOTAS_IGUALES_SIMPLE',
                'ANTICIPO_MAS_CUOTAS_IGUALES',
                'CRONOGRAMA_DEFINIDO',
                'PLAN_POR_BLOQUES'
            ));
    END IF;
END $$;

COMMENT ON COLUMN public.plan_pago_venta.metodo_plan_pago IS
    'Metodo de generacion del plan de pago de venta. PLAN_POR_BLOQUES es el metodo formal para planes V2 estructurados por plan_pago_venta_bloque; CRONOGRAMA_DEFINIDO queda reservado para cronogramas manuales/libres.';
