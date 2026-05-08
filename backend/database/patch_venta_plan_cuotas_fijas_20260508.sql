ALTER TABLE public.venta
DROP CONSTRAINT IF EXISTS chk_venta_tipo_plan_financiero;

ALTER TABLE public.venta
ADD CONSTRAINT chk_venta_tipo_plan_financiero
CHECK (tipo_plan_financiero IN ('CONTADO', 'ANTICIPO_Y_SALDO', 'CUOTAS_FIJAS'));

CREATE TABLE IF NOT EXISTS public.venta_plan_cuota (
    id_venta_plan_cuota bigserial PRIMARY KEY,
    uid_global uuid DEFAULT gen_random_uuid() NOT NULL,
    version_registro integer DEFAULT 1 NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    deleted_at timestamp without time zone,
    id_instalacion_origen bigint,
    id_instalacion_ultima_modificacion bigint,
    op_id_alta uuid,
    op_id_ultima_modificacion uuid,
    id_venta bigint NOT NULL,
    numero_cuota integer NOT NULL,
    importe_cuota numeric(14,2) NOT NULL,
    fecha_vencimiento date NOT NULL,
    moneda character varying(10) NOT NULL,
    observaciones text,
    CONSTRAINT chk_venta_plan_cuota_numero CHECK (numero_cuota > 0),
    CONSTRAINT chk_venta_plan_cuota_importe CHECK (importe_cuota > 0),
    CONSTRAINT chk_venta_plan_cuota_deleted_at CHECK (deleted_at IS NULL OR deleted_at >= created_at),
    CONSTRAINT fk_venta_plan_cuota_venta FOREIGN KEY (id_venta)
        REFERENCES public.venta(id_venta) ON DELETE RESTRICT
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_venta_plan_cuota_activa
ON public.venta_plan_cuota (id_venta, numero_cuota)
WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_venta_plan_cuota_venta
ON public.venta_plan_cuota (id_venta)
WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_venta_plan_cuota_uid_global
ON public.venta_plan_cuota (uid_global);

DROP TRIGGER IF EXISTS trg_bi_venta_plan_cuota_core_ef ON public.venta_plan_cuota;
CREATE TRIGGER trg_bi_venta_plan_cuota_core_ef
BEFORE INSERT ON public.venta_plan_cuota
FOR EACH ROW EXECUTE FUNCTION public.trg_core_ef_sync_defaults_insert();

DROP TRIGGER IF EXISTS trg_bu_venta_plan_cuota_core_ef ON public.venta_plan_cuota;
CREATE TRIGGER trg_bu_venta_plan_cuota_core_ef
BEFORE UPDATE ON public.venta_plan_cuota
FOR EACH ROW EXECUTE FUNCTION public.trg_core_ef_sync_defaults_update();
