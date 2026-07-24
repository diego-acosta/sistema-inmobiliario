-- #393: ciclo de vida definitivo de item_catalogo.
-- Los únicos estados físicos son ACTIVO e INACTIVO. La baja lógica se representa
-- exclusivamente mediante deleted_at y la unicidad de código sigue incluyendo bajas.
BEGIN;

-- La estrategia A normaliza los NULL históricos a ACTIVO, el estado inicial
-- confirmado por EST-ADM y la suite read-only existente. No se preservan valores
-- distintos de los dos estados definitivos: los datos de esta etapa son descartables.
DELETE FROM public.jerarquia_item_catalogo
WHERE id_item_catalogo_padre IN (
        SELECT id_item_catalogo
        FROM public.item_catalogo
        WHERE estado_item_catalogo IS NOT NULL
          AND estado_item_catalogo NOT IN ('ACTIVO', 'INACTIVO')
    )
   OR id_item_catalogo_hijo IN (
        SELECT id_item_catalogo
        FROM public.item_catalogo
        WHERE estado_item_catalogo IS NOT NULL
          AND estado_item_catalogo NOT IN ('ACTIVO', 'INACTIVO')
    );

DELETE FROM public.item_catalogo
WHERE estado_item_catalogo IS NOT NULL
  AND estado_item_catalogo NOT IN ('ACTIVO', 'INACTIVO');

UPDATE public.item_catalogo
SET estado_item_catalogo = 'ACTIVO'
WHERE estado_item_catalogo IS NULL;

ALTER TABLE public.item_catalogo
    ALTER COLUMN estado_item_catalogo SET DEFAULT 'ACTIVO',
    ALTER COLUMN estado_item_catalogo SET NOT NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conrelid = 'public.item_catalogo'::regclass
          AND conname = 'chk_item_catalogo_estado'
    ) THEN
        ALTER TABLE public.item_catalogo
            ADD CONSTRAINT chk_item_catalogo_estado
            CHECK (estado_item_catalogo IN ('ACTIVO', 'INACTIVO'));
    END IF;
END $$;

COMMENT ON COLUMN public.item_catalogo.estado_item_catalogo IS
    'Ciclo de vida #393: ACTIVO o INACTIVO; la baja lógica se expresa con deleted_at.';

COMMIT;
