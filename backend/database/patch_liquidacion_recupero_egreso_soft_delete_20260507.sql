-- Patch idempotente: soporte de soft-delete/anulacion logica para liquidacion_recupero_egreso.

ALTER TABLE public.liquidacion_recupero_egreso
    ADD COLUMN IF NOT EXISTS uid_global uuid NOT NULL DEFAULT gen_random_uuid(),
    ADD COLUMN IF NOT EXISTS version_registro integer NOT NULL DEFAULT 1,
    ADD COLUMN IF NOT EXISTS created_at timestamp without time zone NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ADD COLUMN IF NOT EXISTS updated_at timestamp without time zone NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ADD COLUMN IF NOT EXISTS deleted_at timestamp without time zone,
    ADD COLUMN IF NOT EXISTS id_instalacion_origen bigint,
    ADD COLUMN IF NOT EXISTS id_instalacion_ultima_modificacion bigint,
    ADD COLUMN IF NOT EXISTS op_id_alta uuid,
    ADD COLUMN IF NOT EXISTS op_id_ultima_modificacion uuid,
    ADD COLUMN IF NOT EXISTS estado_liquidacion_recupero_egreso character varying(30) NOT NULL DEFAULT 'ACTIVO';

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'chk_lre_estado'
          AND conrelid = 'public.liquidacion_recupero_egreso'::regclass
    ) THEN
        ALTER TABLE public.liquidacion_recupero_egreso
            ADD CONSTRAINT chk_lre_estado
            CHECK (estado_liquidacion_recupero_egreso IN ('ACTIVO', 'ANULADO'));
    END IF;
END $$;

DROP INDEX IF EXISTS public.ux_lre_egreso_activo;

CREATE UNIQUE INDEX ux_lre_egreso_activo
    ON public.liquidacion_recupero_egreso (id_egreso_proveedor_factura_servicio)
    WHERE deleted_at IS NULL
      AND estado_liquidacion_recupero_egreso = 'ACTIVO';

DROP TRIGGER IF EXISTS trg_bi_lre_core_ef ON public.liquidacion_recupero_egreso;
CREATE TRIGGER trg_bi_lre_core_ef
BEFORE INSERT ON public.liquidacion_recupero_egreso
FOR EACH ROW
EXECUTE FUNCTION public.trg_core_ef_sync_defaults_insert();

DROP TRIGGER IF EXISTS trg_bu_lre_core_ef ON public.liquidacion_recupero_egreso;
CREATE TRIGGER trg_bu_lre_core_ef
BEFORE UPDATE ON public.liquidacion_recupero_egreso
FOR EACH ROW
EXECUTE FUNCTION public.trg_core_ef_sync_defaults_update();
