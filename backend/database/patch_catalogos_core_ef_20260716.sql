-- #363: estructura definitiva CORE-EF para catálogos administrativos.
-- Estrategia: ALTER TABLE con limpieza controlada. Los datos actuales son descartables;
-- no se crean tablas _legacy, espejos, lectura dual ni compatibilidad transitoria.
-- Rollback técnico: restaurar un backup anterior; este patch elimina datos de catálogo.
BEGIN;

-- Las dependencias actuales son historial_catalogo y jerarquia_item_catalogo.
-- Se limpian junto con los catálogos para poder aplicar restricciones definitivas.
TRUNCATE TABLE public.historial_catalogo, public.jerarquia_item_catalogo,
    public.item_catalogo, public.catalogo_maestro RESTART IDENTITY;

ALTER TABLE public.catalogo_maestro
    ADD COLUMN IF NOT EXISTS uid_global uuid DEFAULT gen_random_uuid() NOT NULL,
    ADD COLUMN IF NOT EXISTS version_registro integer DEFAULT 1 NOT NULL,
    ADD COLUMN IF NOT EXISTS created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    ADD COLUMN IF NOT EXISTS updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    ADD COLUMN IF NOT EXISTS deleted_at timestamp without time zone,
    ADD COLUMN IF NOT EXISTS id_instalacion_origen bigint,
    ADD COLUMN IF NOT EXISTS id_instalacion_ultima_modificacion bigint,
    ADD COLUMN IF NOT EXISTS op_id_alta uuid,
    ADD COLUMN IF NOT EXISTS op_id_ultima_modificacion uuid;

ALTER TABLE public.item_catalogo
    ADD COLUMN IF NOT EXISTS uid_global uuid DEFAULT gen_random_uuid() NOT NULL,
    ADD COLUMN IF NOT EXISTS version_registro integer DEFAULT 1 NOT NULL,
    ADD COLUMN IF NOT EXISTS created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    ADD COLUMN IF NOT EXISTS updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    ADD COLUMN IF NOT EXISTS deleted_at timestamp without time zone,
    ADD COLUMN IF NOT EXISTS id_instalacion_origen bigint,
    ADD COLUMN IF NOT EXISTS id_instalacion_ultima_modificacion bigint,
    ADD COLUMN IF NOT EXISTS op_id_alta uuid,
    ADD COLUMN IF NOT EXISTS op_id_ultima_modificacion uuid;

DO $$
DECLARE
    definition text;
BEGIN
    FOR definition IN SELECT unnest(ARRAY[
        'ALTER TABLE public.catalogo_maestro ADD CONSTRAINT uq_catalogo_maestro_uid_global UNIQUE (uid_global)',
        'ALTER TABLE public.catalogo_maestro ADD CONSTRAINT uq_catalogo_maestro_codigo UNIQUE (codigo_catalogo_maestro)',
        'ALTER TABLE public.catalogo_maestro ADD CONSTRAINT chk_catalogo_maestro_version_registro CHECK (version_registro >= 1)',
        'ALTER TABLE public.catalogo_maestro ADD CONSTRAINT chk_catalogo_maestro_deleted_at CHECK (deleted_at IS NULL OR deleted_at >= created_at)',
        'ALTER TABLE public.catalogo_maestro ADD CONSTRAINT fk_catalogo_maestro_instalacion_origen FOREIGN KEY (id_instalacion_origen) REFERENCES public.instalacion(id_instalacion) ON DELETE RESTRICT',
        'ALTER TABLE public.catalogo_maestro ADD CONSTRAINT fk_catalogo_maestro_instalacion_ultima_modificacion FOREIGN KEY (id_instalacion_ultima_modificacion) REFERENCES public.instalacion(id_instalacion) ON DELETE RESTRICT',
        'ALTER TABLE public.item_catalogo ADD CONSTRAINT uq_item_catalogo_uid_global UNIQUE (uid_global)',
        'ALTER TABLE public.item_catalogo ADD CONSTRAINT chk_item_catalogo_version_registro CHECK (version_registro >= 1)',
        'ALTER TABLE public.item_catalogo ADD CONSTRAINT chk_item_catalogo_deleted_at CHECK (deleted_at IS NULL OR deleted_at >= created_at)',
        'ALTER TABLE public.item_catalogo ADD CONSTRAINT fk_item_catalogo_instalacion_origen FOREIGN KEY (id_instalacion_origen) REFERENCES public.instalacion(id_instalacion) ON DELETE RESTRICT',
        'ALTER TABLE public.item_catalogo ADD CONSTRAINT fk_item_catalogo_instalacion_ultima_modificacion FOREIGN KEY (id_instalacion_ultima_modificacion) REFERENCES public.instalacion(id_instalacion) ON DELETE RESTRICT'
    ]) LOOP
        IF NOT EXISTS (
            SELECT 1 FROM pg_constraint
            WHERE conname = split_part(split_part(definition, ' ADD CONSTRAINT ', 2), ' ', 1)
        ) THEN
            EXECUTE definition;
        END IF;
    END LOOP;
END $$;

-- La unicidad del código se aplica a todas las filas, incluidas bajas lógicas:
-- no hay evidencia que autorice reutilización ni reactivación con un código histórico.
CREATE UNIQUE INDEX IF NOT EXISTS ux_catalogo_maestro_op_id_alta
    ON public.catalogo_maestro (op_id_alta) WHERE op_id_alta IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS ux_item_catalogo_op_id_alta
    ON public.item_catalogo (op_id_alta) WHERE op_id_alta IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_catalogo_maestro_uid_global ON public.catalogo_maestro (uid_global);
CREATE INDEX IF NOT EXISTS idx_item_catalogo_uid_global ON public.item_catalogo (uid_global);
CREATE INDEX IF NOT EXISTS idx_item_catalogo_catalogo ON public.item_catalogo (id_catalogo_maestro);
CREATE INDEX IF NOT EXISTS idx_item_catalogo_catalogo_estado ON public.item_catalogo (id_catalogo_maestro, estado_item_catalogo);

DROP TRIGGER IF EXISTS trg_bi_catalogo_maestro_core_ef ON public.catalogo_maestro;
CREATE TRIGGER trg_bi_catalogo_maestro_core_ef
    BEFORE INSERT ON public.catalogo_maestro
    FOR EACH ROW EXECUTE FUNCTION public.trg_core_ef_sync_defaults_insert();
DROP TRIGGER IF EXISTS trg_bu_catalogo_maestro_core_ef ON public.catalogo_maestro;
CREATE TRIGGER trg_bu_catalogo_maestro_core_ef
    BEFORE UPDATE ON public.catalogo_maestro
    FOR EACH ROW EXECUTE FUNCTION public.trg_core_ef_sync_defaults_update();
DROP TRIGGER IF EXISTS trg_bi_item_catalogo_core_ef ON public.item_catalogo;
CREATE TRIGGER trg_bi_item_catalogo_core_ef
    BEFORE INSERT ON public.item_catalogo
    FOR EACH ROW EXECUTE FUNCTION public.trg_core_ef_sync_defaults_insert();
DROP TRIGGER IF EXISTS trg_bu_item_catalogo_core_ef ON public.item_catalogo;
CREATE TRIGGER trg_bu_item_catalogo_core_ef
    BEFORE UPDATE ON public.item_catalogo
    FOR EACH ROW EXECUTE FUNCTION public.trg_core_ef_sync_defaults_update();

COMMIT;
