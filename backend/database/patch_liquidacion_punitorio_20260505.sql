BEGIN;

CREATE TABLE IF NOT EXISTS public.liquidacion_punitorio (
    id_liquidacion_punitorio bigserial PRIMARY KEY,
    uid_global uuid DEFAULT gen_random_uuid() NOT NULL,
    version_registro integer DEFAULT 1 NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    deleted_at timestamp without time zone,
    id_instalacion_origen bigint,
    id_instalacion_ultima_modificacion bigint,
    op_id_alta uuid,
    op_id_ultima_modificacion uuid,
    id_obligacion_financiera bigint NOT NULL,
    id_composicion_obligacion bigint NOT NULL,
    uid_pago_grupo uuid NOT NULL,
    codigo_pago_grupo character varying(50) NOT NULL,
    fecha_vencimiento date NOT NULL,
    fecha_inicio_calculo date NOT NULL,
    fecha_fin_calculo date NOT NULL,
    base_morable numeric(14,2) NOT NULL,
    tasa_diaria numeric(12,8) NOT NULL,
    dias_calculados integer NOT NULL,
    importe_liquidado numeric(14,2) NOT NULL,
    estado_liquidacion character varying(30) DEFAULT 'ACTIVA'::character varying NOT NULL,
    CONSTRAINT chk_liquidacion_punitorio_deleted_at CHECK (deleted_at IS NULL OR deleted_at >= created_at),
    CONSTRAINT chk_liquidacion_punitorio_estado CHECK (estado_liquidacion IN ('ACTIVA', 'REVERSADA', 'ANULADA')),
    CONSTRAINT chk_liquidacion_punitorio_fechas CHECK (fecha_inicio_calculo <= fecha_fin_calculo),
    CONSTRAINT chk_liquidacion_punitorio_importes CHECK (
        base_morable >= 0
        AND tasa_diaria >= 0
        AND dias_calculados >= 0
        AND importe_liquidado > 0
    )
);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'uq_liquidacion_punitorio_uid_global'
    ) THEN
        ALTER TABLE public.liquidacion_punitorio
            ADD CONSTRAINT uq_liquidacion_punitorio_uid_global UNIQUE (uid_global);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'fk_lp_obligacion'
    ) THEN
        ALTER TABLE public.liquidacion_punitorio
            ADD CONSTRAINT fk_lp_obligacion
            FOREIGN KEY (id_obligacion_financiera)
            REFERENCES public.obligacion_financiera(id_obligacion_financiera)
            ON DELETE RESTRICT;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'fk_lp_composicion'
    ) THEN
        ALTER TABLE public.liquidacion_punitorio
            ADD CONSTRAINT fk_lp_composicion
            FOREIGN KEY (id_composicion_obligacion)
            REFERENCES public.composicion_obligacion(id_composicion_obligacion)
            ON DELETE RESTRICT;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_liquidacion_punitorio_codigo_pago_grupo
    ON public.liquidacion_punitorio USING btree (codigo_pago_grupo);

CREATE INDEX IF NOT EXISTS idx_liquidacion_punitorio_uid_pago_grupo
    ON public.liquidacion_punitorio USING btree (uid_pago_grupo);

CREATE INDEX IF NOT EXISTS idx_liquidacion_punitorio_obligacion
    ON public.liquidacion_punitorio USING btree (id_obligacion_financiera);

CREATE INDEX IF NOT EXISTS idx_liquidacion_punitorio_uid_global
    ON public.liquidacion_punitorio USING btree (uid_global);

CREATE UNIQUE INDEX IF NOT EXISTS uq_liquidacion_punitorio_op_obligacion
    ON public.liquidacion_punitorio USING btree (op_id_alta, id_obligacion_financiera)
    WHERE op_id_alta IS NOT NULL AND deleted_at IS NULL;

DROP TRIGGER IF EXISTS trg_bi_liquidacion_punitorio_core_ef ON public.liquidacion_punitorio;
CREATE TRIGGER trg_bi_liquidacion_punitorio_core_ef
    BEFORE INSERT ON public.liquidacion_punitorio
    FOR EACH ROW EXECUTE FUNCTION public.trg_core_ef_sync_defaults_insert();

DROP TRIGGER IF EXISTS trg_bu_liquidacion_punitorio_core_ef ON public.liquidacion_punitorio;
CREATE TRIGGER trg_bu_liquidacion_punitorio_core_ef
    BEFORE UPDATE ON public.liquidacion_punitorio
    FOR EACH ROW EXECUTE FUNCTION public.trg_core_ef_sync_defaults_update();

COMMIT;
