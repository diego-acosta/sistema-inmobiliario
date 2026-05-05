-- Parametros formales de punitorio/mora V1.
-- Idempotente: crea la tabla de parametros y deja un parametro GLOBAL inicial.

CREATE TABLE IF NOT EXISTS public.parametro_punitorio (
    id_parametro_punitorio bigserial PRIMARY KEY,
    uid_global uuid DEFAULT gen_random_uuid() NOT NULL,
    version_registro integer DEFAULT 1 NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    deleted_at timestamp without time zone,
    id_instalacion_origen bigint,
    id_instalacion_ultima_modificacion bigint,
    op_id_alta uuid,
    op_id_ultima_modificacion uuid,
    alcance_tipo character varying(50) NOT NULL,
    id_relacion_generadora bigint,
    id_concepto_financiero bigint,
    tasa_diaria numeric(10,6) NOT NULL,
    dias_gracia integer NOT NULL,
    fecha_desde date NOT NULL,
    fecha_hasta date,
    estado_parametro character varying(30) DEFAULT 'ACTIVO'::character varying NOT NULL
);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'uq_parametro_punitorio_uid_global'
          AND conrelid = 'public.parametro_punitorio'::regclass
    ) THEN
        ALTER TABLE public.parametro_punitorio
            ADD CONSTRAINT uq_parametro_punitorio_uid_global UNIQUE (uid_global);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'chk_parametro_punitorio_alcance'
          AND conrelid = 'public.parametro_punitorio'::regclass
    ) THEN
        ALTER TABLE public.parametro_punitorio
            ADD CONSTRAINT chk_parametro_punitorio_alcance
            CHECK (alcance_tipo IN ('GLOBAL', 'CONCEPTO', 'RELACION_GENERADORA'));
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'chk_parametro_punitorio_estado'
          AND conrelid = 'public.parametro_punitorio'::regclass
    ) THEN
        ALTER TABLE public.parametro_punitorio
            ADD CONSTRAINT chk_parametro_punitorio_estado
            CHECK (estado_parametro IN ('ACTIVO', 'INACTIVO'));
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'chk_parametro_punitorio_valores'
          AND conrelid = 'public.parametro_punitorio'::regclass
    ) THEN
        ALTER TABLE public.parametro_punitorio
            ADD CONSTRAINT chk_parametro_punitorio_valores
            CHECK (tasa_diaria >= 0 AND dias_gracia >= 0);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'chk_parametro_punitorio_vigencia'
          AND conrelid = 'public.parametro_punitorio'::regclass
    ) THEN
        ALTER TABLE public.parametro_punitorio
            ADD CONSTRAINT chk_parametro_punitorio_vigencia
            CHECK (fecha_hasta IS NULL OR fecha_hasta >= fecha_desde);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'chk_parametro_punitorio_scope'
          AND conrelid = 'public.parametro_punitorio'::regclass
    ) THEN
        ALTER TABLE public.parametro_punitorio
            ADD CONSTRAINT chk_parametro_punitorio_scope
            CHECK (
                (alcance_tipo = 'GLOBAL' AND id_relacion_generadora IS NULL AND id_concepto_financiero IS NULL)
                OR (alcance_tipo = 'CONCEPTO' AND id_relacion_generadora IS NULL AND id_concepto_financiero IS NOT NULL)
                OR (alcance_tipo = 'RELACION_GENERADORA' AND id_relacion_generadora IS NOT NULL AND id_concepto_financiero IS NULL)
            );
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'fk_pp_relacion_generadora'
          AND conrelid = 'public.parametro_punitorio'::regclass
    ) THEN
        ALTER TABLE public.parametro_punitorio
            ADD CONSTRAINT fk_pp_relacion_generadora
            FOREIGN KEY (id_relacion_generadora)
            REFERENCES public.relacion_generadora(id_relacion_generadora)
            ON DELETE RESTRICT;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'fk_pp_concepto_financiero'
          AND conrelid = 'public.parametro_punitorio'::regclass
    ) THEN
        ALTER TABLE public.parametro_punitorio
            ADD CONSTRAINT fk_pp_concepto_financiero
            FOREIGN KEY (id_concepto_financiero)
            REFERENCES public.concepto_financiero(id_concepto_financiero)
            ON DELETE RESTRICT;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_parametro_punitorio_scope_vigencia
    ON public.parametro_punitorio (
        alcance_tipo,
        id_relacion_generadora,
        id_concepto_financiero,
        fecha_desde,
        fecha_hasta
    )
    WHERE deleted_at IS NULL AND estado_parametro = 'ACTIVO';

CREATE INDEX IF NOT EXISTS idx_parametro_punitorio_uid_global
    ON public.parametro_punitorio (uid_global);

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_proc
        WHERE proname = 'trg_core_ef_sync_defaults_insert'
    )
    AND NOT EXISTS (
        SELECT 1 FROM pg_trigger
        WHERE tgname = 'trg_bi_parametro_punitorio_core_ef'
    ) THEN
        CREATE TRIGGER trg_bi_parametro_punitorio_core_ef
        BEFORE INSERT ON public.parametro_punitorio
        FOR EACH ROW
        EXECUTE FUNCTION public.trg_core_ef_sync_defaults_insert();
    END IF;

    IF EXISTS (
        SELECT 1 FROM pg_proc
        WHERE proname = 'trg_core_ef_sync_defaults_update'
    )
    AND NOT EXISTS (
        SELECT 1 FROM pg_trigger
        WHERE tgname = 'trg_bu_parametro_punitorio_core_ef'
    ) THEN
        CREATE TRIGGER trg_bu_parametro_punitorio_core_ef
        BEFORE UPDATE ON public.parametro_punitorio
        FOR EACH ROW
        EXECUTE FUNCTION public.trg_core_ef_sync_defaults_update();
    END IF;
END $$;

INSERT INTO public.parametro_punitorio (
    alcance_tipo,
    tasa_diaria,
    dias_gracia,
    fecha_desde,
    estado_parametro
)
SELECT
    'GLOBAL',
    0.001000,
    5,
    DATE '1900-01-01',
    'ACTIVO'
WHERE NOT EXISTS (
    SELECT 1
    FROM public.parametro_punitorio
    WHERE alcance_tipo = 'GLOBAL'
      AND id_relacion_generadora IS NULL
      AND id_concepto_financiero IS NULL
      AND fecha_desde = DATE '1900-01-01'
      AND deleted_at IS NULL
);
