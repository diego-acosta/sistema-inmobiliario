-- Patch V2: bloques estructurales para planes de pago de venta.
-- plan_pago_venta_bloque describe reglas comerciales; no representa deuda.

CREATE TABLE IF NOT EXISTS public.plan_pago_venta_bloque (
    id_plan_pago_venta_bloque bigserial PRIMARY KEY,
    uid_global uuid DEFAULT gen_random_uuid() NOT NULL,
    version_registro integer DEFAULT 1 NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    deleted_at timestamp without time zone NULL,
    id_instalacion_origen bigint NULL,
    id_instalacion_ultima_modificacion bigint NULL,
    op_id_alta uuid NULL,
    op_id_ultima_modificacion uuid NULL,

    id_plan_pago_venta bigint NOT NULL,
    numero_bloque integer NOT NULL,
    tipo_bloque varchar(30) NOT NULL,
    etiqueta_bloque varchar(120) NULL,
    clave_bloque varchar(160) NOT NULL,
    cantidad_cuotas integer NULL,
    importe_total_bloque numeric(14,2) NULL,
    importe_cuota numeric(14,2) NULL,
    fecha_vencimiento date NULL,
    fecha_primer_vencimiento date NULL,
    periodicidad varchar(30) NULL,
    regla_redondeo varchar(30) NULL,
    concepto_financiero_codigo varchar(50) NULL,
    observaciones text NULL
);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'fk_ppvb_plan_pago_venta'
          AND conrelid = 'public.plan_pago_venta_bloque'::regclass
    ) THEN
        ALTER TABLE public.plan_pago_venta_bloque
            ADD CONSTRAINT fk_ppvb_plan_pago_venta
            FOREIGN KEY (id_plan_pago_venta)
            REFERENCES public.plan_pago_venta(id_plan_pago_venta)
            ON DELETE RESTRICT;
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'chk_ppvb_deleted_at'
          AND conrelid = 'public.plan_pago_venta_bloque'::regclass
    ) THEN
        ALTER TABLE public.plan_pago_venta_bloque
            ADD CONSTRAINT chk_ppvb_deleted_at
            CHECK (deleted_at IS NULL OR deleted_at >= created_at);
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'chk_ppvb_numero_bloque'
          AND conrelid = 'public.plan_pago_venta_bloque'::regclass
    ) THEN
        ALTER TABLE public.plan_pago_venta_bloque
            ADD CONSTRAINT chk_ppvb_numero_bloque
            CHECK (numero_bloque > 0);
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'chk_ppvb_tipo_bloque'
          AND conrelid = 'public.plan_pago_venta_bloque'::regclass
    ) THEN
        ALTER TABLE public.plan_pago_venta_bloque
            ADD CONSTRAINT chk_ppvb_tipo_bloque
            CHECK (tipo_bloque IN ('CONTADO', 'ANTICIPO', 'TRAMO_CUOTAS', 'REFUERZO', 'SALDO'));
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'chk_ppvb_cantidad_cuotas'
          AND conrelid = 'public.plan_pago_venta_bloque'::regclass
    ) THEN
        ALTER TABLE public.plan_pago_venta_bloque
            ADD CONSTRAINT chk_ppvb_cantidad_cuotas
            CHECK (cantidad_cuotas IS NULL OR cantidad_cuotas > 0);
    END IF;
END $$;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'chk_ppvb_importe_total_bloque'
          AND conrelid = 'public.plan_pago_venta_bloque'::regclass
          AND (
              pg_get_constraintdef(oid) ~ 'importe_total_bloque\s*>=\s*\(?0'
              OR pg_get_constraintdef(oid) !~ 'importe_total_bloque\s*>\s*\(?0'
          )
    ) THEN
        ALTER TABLE public.plan_pago_venta_bloque
            DROP CONSTRAINT chk_ppvb_importe_total_bloque;
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'chk_ppvb_importe_total_bloque'
          AND conrelid = 'public.plan_pago_venta_bloque'::regclass
    ) THEN
        ALTER TABLE public.plan_pago_venta_bloque
            ADD CONSTRAINT chk_ppvb_importe_total_bloque
            CHECK (importe_total_bloque IS NULL OR importe_total_bloque > 0);
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'chk_ppvb_importe_cuota'
          AND conrelid = 'public.plan_pago_venta_bloque'::regclass
    ) THEN
        ALTER TABLE public.plan_pago_venta_bloque
            ADD CONSTRAINT chk_ppvb_importe_cuota
            CHECK (importe_cuota IS NULL OR importe_cuota > 0);
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'chk_ppvb_tramo_cuotas_requeridos'
          AND conrelid = 'public.plan_pago_venta_bloque'::regclass
    ) THEN
        ALTER TABLE public.plan_pago_venta_bloque
            ADD CONSTRAINT chk_ppvb_tramo_cuotas_requeridos
            CHECK (
                tipo_bloque <> 'TRAMO_CUOTAS'
                OR (
                    cantidad_cuotas IS NOT NULL
                    AND importe_cuota IS NOT NULL
                    AND fecha_primer_vencimiento IS NOT NULL
                    AND periodicidad IS NOT NULL
                )
            );
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'chk_ppvb_pago_unico_requeridos'
          AND conrelid = 'public.plan_pago_venta_bloque'::regclass
    ) THEN
        ALTER TABLE public.plan_pago_venta_bloque
            ADD CONSTRAINT chk_ppvb_pago_unico_requeridos
            CHECK (
                tipo_bloque NOT IN ('CONTADO', 'ANTICIPO', 'REFUERZO', 'SALDO')
                OR (
                    importe_total_bloque IS NOT NULL
                    AND fecha_vencimiento IS NOT NULL
                )
            );
    END IF;
END $$;

ALTER TABLE public.obligacion_financiera
    ADD COLUMN IF NOT EXISTS id_plan_pago_venta_bloque bigint NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'fk_obl_plan_pago_venta_bloque'
          AND conrelid = 'public.obligacion_financiera'::regclass
    ) THEN
        ALTER TABLE public.obligacion_financiera
            ADD CONSTRAINT fk_obl_plan_pago_venta_bloque
            FOREIGN KEY (id_plan_pago_venta_bloque)
            REFERENCES public.plan_pago_venta_bloque(id_plan_pago_venta_bloque)
            ON DELETE RESTRICT;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_ppvb_uid_global
    ON public.plan_pago_venta_bloque(uid_global);

CREATE INDEX IF NOT EXISTS idx_ppvb_plan_pago_venta
    ON public.plan_pago_venta_bloque(id_plan_pago_venta)
    WHERE deleted_at IS NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_ppvb_plan_numero
    ON public.plan_pago_venta_bloque(id_plan_pago_venta, numero_bloque)
    WHERE deleted_at IS NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_ppvb_plan_clave
    ON public.plan_pago_venta_bloque(id_plan_pago_venta, clave_bloque)
    WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_obl_plan_pago_venta_bloque
    ON public.obligacion_financiera(id_plan_pago_venta_bloque)
    WHERE deleted_at IS NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_trigger
        WHERE tgname = 'trg_bi_ppvb_core_ef'
          AND tgrelid = 'public.plan_pago_venta_bloque'::regclass
    ) THEN
        CREATE TRIGGER trg_bi_ppvb_core_ef
        BEFORE INSERT ON public.plan_pago_venta_bloque
        FOR EACH ROW EXECUTE FUNCTION public.trg_core_ef_sync_defaults_insert();
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_trigger
        WHERE tgname = 'trg_bu_ppvb_core_ef'
          AND tgrelid = 'public.plan_pago_venta_bloque'::regclass
    ) THEN
        CREATE TRIGGER trg_bu_ppvb_core_ef
        BEFORE UPDATE ON public.plan_pago_venta_bloque
        FOR EACH ROW EXECUTE FUNCTION public.trg_core_ef_sync_defaults_update();
    END IF;
END $$;

COMMENT ON TABLE public.plan_pago_venta_bloque IS
    'Estructura/regla comercial de un plan de pago de venta. No representa deuda, cuota financiera ni obligacion exigible; la deuda se materializa exclusivamente en obligacion_financiera.';

COMMENT ON COLUMN public.plan_pago_venta_bloque.clave_bloque IS
    'Clave estable del bloque dentro del plan de pago de venta; no reemplaza clave_funcional_origen de obligacion_financiera.';

COMMENT ON COLUMN public.plan_pago_venta_bloque.tipo_bloque IS
    'Tipo estructural comercial inicial: CONTADO, ANTICIPO, TRAMO_CUOTAS, REFUERZO o SALDO. No equivale necesariamente a obligacion_financiera.tipo_item_cronograma.';

COMMENT ON COLUMN public.plan_pago_venta_bloque.concepto_financiero_codigo IS
    'Codigo conceptual sugerido para la futura materializacion financiera; queda libre y sin FK por ahora hasta confirmar el mapeo definitivo.';

COMMENT ON COLUMN public.obligacion_financiera.id_plan_pago_venta_bloque IS
    'Trazabilidad hacia el bloque comercial que origino la obligacion; no es la clave de idempotencia.';

COMMENT ON COLUMN public.obligacion_financiera.clave_funcional_origen IS
    'Clave idempotente funcional de la obligacion generada.';
