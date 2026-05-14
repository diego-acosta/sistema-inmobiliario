-- patch_plan_pago_venta_cronograma_v2_20260514.sql
-- Soporte SQL minimo para cronograma V2 de planes de pago de venta.
--
-- Decisiones:
-- - plan_pago_venta es cabecera/regla comercial: no contiene cuotas,
--   no representa deuda y no reemplaza obligacion_financiera.
-- - generacion_cronograma_financiero es una corrida tecnica/idempotente:
--   no representa cuotas, no reemplaza obligaciones y permite auditar
--   generaciones de cronograma.
-- - obligacion_financiera representa cada item exigible/proyectado del
--   cronograma; composicion_obligacion guarda el desglose y
--   obligacion_obligado guarda responsables.
-- - venta_plan_cuota queda intacta como compatibilidad heredada V1 para
--   CUOTAS_FIJAS. Este patch no la modifica.
-- - No se crean plan_pago_venta_cuota ni plan_pago_venta_tramo.

-- Diagnostico previo: obligaciones activas duplicadas por clave funcional.
-- En una instalacion sin los campos V2, esta consulta queda omitida.
DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'obligacion_financiera'
          AND column_name = 'clave_funcional_origen'
    ) THEN
        RAISE NOTICE 'Diagnostico: revisar duplicados activos en obligacion_financiera por (id_relacion_generadora, clave_funcional_origen).';
    ELSE
        RAISE NOTICE 'Diagnostico: obligacion_financiera.clave_funcional_origen aun no existe; no hay duplicados V2 previos que validar.';
    END IF;
END $$;

-- Diagnostico previo: planes vivos duplicados por venta si la tabla existia.
DO $$
BEGIN
    IF to_regclass('public.plan_pago_venta') IS NOT NULL THEN
        RAISE NOTICE 'Diagnostico: revisar duplicados de planes vivos por id_venta en plan_pago_venta antes del unique parcial.';
    ELSE
        RAISE NOTICE 'Diagnostico: plan_pago_venta aun no existe; no hay planes vivos previos que validar.';
    END IF;
END $$;

-- Diagnostico previo: corridas activas duplicadas si la tabla existia.
DO $$
BEGIN
    IF to_regclass('public.generacion_cronograma_financiero') IS NOT NULL THEN
        RAISE NOTICE 'Diagnostico: revisar duplicados activos por (id_relacion_generadora, clave_generacion) en generacion_cronograma_financiero.';
    ELSE
        RAISE NOTICE 'Diagnostico: generacion_cronograma_financiero aun no existe; no hay corridas previas que validar.';
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS public.plan_pago_venta (
    id_plan_pago_venta bigserial PRIMARY KEY,
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
    metodo_plan_pago character varying(50) NOT NULL,
    estado_plan_pago character varying(30) DEFAULT 'BORRADOR' NOT NULL,
    moneda character varying(10) DEFAULT 'ARS' NOT NULL,
    monto_total_plan numeric(14,2) NOT NULL,
    cantidad_cuotas integer,
    periodicidad character varying(30),
    fecha_primer_vencimiento date,
    importe_anticipo numeric(14,2),
    fecha_vencimiento_anticipo date,
    regla_redondeo character varying(30),
    observaciones text
);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'fk_plan_pago_venta_venta'
          AND conrelid = 'public.plan_pago_venta'::regclass
    ) THEN
        ALTER TABLE public.plan_pago_venta
        ADD CONSTRAINT fk_plan_pago_venta_venta
        FOREIGN KEY (id_venta)
        REFERENCES public.venta(id_venta)
        ON DELETE RESTRICT;
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'chk_plan_pago_venta_deleted_at'
          AND conrelid = 'public.plan_pago_venta'::regclass
    ) THEN
        ALTER TABLE public.plan_pago_venta
        ADD CONSTRAINT chk_plan_pago_venta_deleted_at
        CHECK (deleted_at IS NULL OR deleted_at >= created_at);
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'chk_plan_pago_venta_metodo'
          AND conrelid = 'public.plan_pago_venta'::regclass
    ) THEN
        ALTER TABLE public.plan_pago_venta
        ADD CONSTRAINT chk_plan_pago_venta_metodo
        CHECK (metodo_plan_pago IN (
            'CUOTAS_IGUALES_SIMPLE',
            'ANTICIPO_MAS_CUOTAS_IGUALES',
            'CRONOGRAMA_DEFINIDO'
        ));
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'chk_plan_pago_venta_estado'
          AND conrelid = 'public.plan_pago_venta'::regclass
    ) THEN
        ALTER TABLE public.plan_pago_venta
        ADD CONSTRAINT chk_plan_pago_venta_estado
        CHECK (estado_plan_pago IN (
            'BORRADOR',
            'ACTIVO',
            'GENERADO',
            'REEMPLAZADO',
            'ANULADO'
        ));
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'chk_plan_pago_venta_monto'
          AND conrelid = 'public.plan_pago_venta'::regclass
    ) THEN
        ALTER TABLE public.plan_pago_venta
        ADD CONSTRAINT chk_plan_pago_venta_monto
        CHECK (monto_total_plan > 0);
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'chk_plan_pago_venta_cantidad'
          AND conrelid = 'public.plan_pago_venta'::regclass
    ) THEN
        ALTER TABLE public.plan_pago_venta
        ADD CONSTRAINT chk_plan_pago_venta_cantidad
        CHECK (cantidad_cuotas IS NULL OR cantidad_cuotas > 0);
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'chk_plan_pago_venta_importe_anticipo'
          AND conrelid = 'public.plan_pago_venta'::regclass
    ) THEN
        ALTER TABLE public.plan_pago_venta
        ADD CONSTRAINT chk_plan_pago_venta_importe_anticipo
        CHECK (importe_anticipo IS NULL OR importe_anticipo >= 0);
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_plan_pago_venta_uid_global
ON public.plan_pago_venta (uid_global);

CREATE INDEX IF NOT EXISTS idx_plan_pago_venta_venta
ON public.plan_pago_venta (id_venta)
WHERE deleted_at IS NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_plan_pago_venta_activo
ON public.plan_pago_venta (id_venta)
WHERE deleted_at IS NULL
  AND estado_plan_pago IN ('BORRADOR', 'ACTIVO', 'GENERADO');

COMMENT ON TABLE public.plan_pago_venta IS
'Cabecera/regla comercial V2 de plan de pago de venta. No contiene cuotas, no representa deuda y no reemplaza obligacion_financiera.';

COMMENT ON COLUMN public.plan_pago_venta.metodo_plan_pago IS
'Metodo comercial pactado para generar cronograma V2. Los items exigibles/proyectados se materializan en obligacion_financiera.';

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_trigger
        WHERE tgname = 'trg_bi_plan_pago_venta_core_ef'
          AND tgrelid = 'public.plan_pago_venta'::regclass
    ) THEN
        CREATE TRIGGER trg_bi_plan_pago_venta_core_ef
        BEFORE INSERT ON public.plan_pago_venta
        FOR EACH ROW EXECUTE FUNCTION public.trg_core_ef_sync_defaults_insert();
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_trigger
        WHERE tgname = 'trg_bu_plan_pago_venta_core_ef'
          AND tgrelid = 'public.plan_pago_venta'::regclass
    ) THEN
        CREATE TRIGGER trg_bu_plan_pago_venta_core_ef
        BEFORE UPDATE ON public.plan_pago_venta
        FOR EACH ROW EXECUTE FUNCTION public.trg_core_ef_sync_defaults_update();
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS public.generacion_cronograma_financiero (
    id_generacion_cronograma_financiero bigserial PRIMARY KEY,
    uid_global uuid DEFAULT gen_random_uuid() NOT NULL,
    version_registro integer DEFAULT 1 NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    deleted_at timestamp without time zone,
    id_instalacion_origen bigint,
    id_instalacion_ultima_modificacion bigint,
    op_id_alta uuid,
    op_id_ultima_modificacion uuid,
    id_relacion_generadora bigint NOT NULL,
    id_plan_pago_venta bigint,
    tipo_generacion character varying(50) NOT NULL,
    clave_generacion character varying(120) NOT NULL,
    estado_generacion character varying(30) DEFAULT 'GENERADA' NOT NULL,
    fecha_generacion timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    observaciones text
);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'fk_gcf_relacion_generadora'
          AND conrelid = 'public.generacion_cronograma_financiero'::regclass
    ) THEN
        ALTER TABLE public.generacion_cronograma_financiero
        ADD CONSTRAINT fk_gcf_relacion_generadora
        FOREIGN KEY (id_relacion_generadora)
        REFERENCES public.relacion_generadora(id_relacion_generadora)
        ON DELETE RESTRICT;
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'fk_gcf_plan_pago_venta'
          AND conrelid = 'public.generacion_cronograma_financiero'::regclass
    ) THEN
        ALTER TABLE public.generacion_cronograma_financiero
        ADD CONSTRAINT fk_gcf_plan_pago_venta
        FOREIGN KEY (id_plan_pago_venta)
        REFERENCES public.plan_pago_venta(id_plan_pago_venta)
        ON DELETE RESTRICT;
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'chk_gcf_deleted_at'
          AND conrelid = 'public.generacion_cronograma_financiero'::regclass
    ) THEN
        ALTER TABLE public.generacion_cronograma_financiero
        ADD CONSTRAINT chk_gcf_deleted_at
        CHECK (deleted_at IS NULL OR deleted_at >= created_at);
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'chk_gcf_tipo'
          AND conrelid = 'public.generacion_cronograma_financiero'::regclass
    ) THEN
        ALTER TABLE public.generacion_cronograma_financiero
        ADD CONSTRAINT chk_gcf_tipo
        CHECK (tipo_generacion IN (
            'PLAN_PAGO_VENTA_V2',
            'MIGRACION_VENTA_PLAN_CUOTA_V1'
        ));
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'chk_gcf_estado'
          AND conrelid = 'public.generacion_cronograma_financiero'::regclass
    ) THEN
        ALTER TABLE public.generacion_cronograma_financiero
        ADD CONSTRAINT chk_gcf_estado
        CHECK (estado_generacion IN (
            'GENERADA',
            'REEMPLAZADA',
            'ANULADA',
            'FALLIDA'
        ));
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_gcf_uid_global
ON public.generacion_cronograma_financiero (uid_global);

CREATE INDEX IF NOT EXISTS idx_gcf_relacion_generadora
ON public.generacion_cronograma_financiero (id_relacion_generadora)
WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_gcf_plan_pago_venta
ON public.generacion_cronograma_financiero (id_plan_pago_venta)
WHERE deleted_at IS NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_gcf_clave_activa
ON public.generacion_cronograma_financiero (
    id_relacion_generadora,
    clave_generacion
)
WHERE deleted_at IS NULL
  AND estado_generacion <> 'ANULADA';

COMMENT ON TABLE public.generacion_cronograma_financiero IS
'Corrida tecnica/idempotente de generacion de cronograma financiero. No representa cuotas ni reemplaza obligaciones.';

COMMENT ON COLUMN public.generacion_cronograma_financiero.clave_generacion IS
'Clave idempotente de la corrida de generacion dentro de la relacion generadora.';

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_trigger
        WHERE tgname = 'trg_bi_gcf_core_ef'
          AND tgrelid = 'public.generacion_cronograma_financiero'::regclass
    ) THEN
        CREATE TRIGGER trg_bi_gcf_core_ef
        BEFORE INSERT ON public.generacion_cronograma_financiero
        FOR EACH ROW EXECUTE FUNCTION public.trg_core_ef_sync_defaults_insert();
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_trigger
        WHERE tgname = 'trg_bu_gcf_core_ef'
          AND tgrelid = 'public.generacion_cronograma_financiero'::regclass
    ) THEN
        CREATE TRIGGER trg_bu_gcf_core_ef
        BEFORE UPDATE ON public.generacion_cronograma_financiero
        FOR EACH ROW EXECUTE FUNCTION public.trg_core_ef_sync_defaults_update();
    END IF;
END $$;

ALTER TABLE public.obligacion_financiera
ADD COLUMN IF NOT EXISTS id_generacion_cronograma_financiero bigint,
ADD COLUMN IF NOT EXISTS numero_obligacion integer,
ADD COLUMN IF NOT EXISTS tipo_item_cronograma character varying(30),
ADD COLUMN IF NOT EXISTS etiqueta_obligacion character varying(120),
ADD COLUMN IF NOT EXISTS clave_funcional_origen character varying(160);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'fk_obl_generacion_cronograma'
          AND conrelid = 'public.obligacion_financiera'::regclass
    ) THEN
        ALTER TABLE public.obligacion_financiera
        ADD CONSTRAINT fk_obl_generacion_cronograma
        FOREIGN KEY (id_generacion_cronograma_financiero)
        REFERENCES public.generacion_cronograma_financiero(id_generacion_cronograma_financiero)
        ON DELETE RESTRICT;
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'chk_obl_numero_obligacion'
          AND conrelid = 'public.obligacion_financiera'::regclass
    ) THEN
        ALTER TABLE public.obligacion_financiera
        ADD CONSTRAINT chk_obl_numero_obligacion
        CHECK (numero_obligacion IS NULL OR numero_obligacion > 0);
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'chk_obl_tipo_item_cronograma'
          AND conrelid = 'public.obligacion_financiera'::regclass
    ) THEN
        ALTER TABLE public.obligacion_financiera
        ADD CONSTRAINT chk_obl_tipo_item_cronograma
        CHECK (
            tipo_item_cronograma IS NULL OR
            tipo_item_cronograma IN (
                'ANTICIPO',
                'CUOTA',
                'SALDO',
                'REFUERZO',
                'AJUSTE',
                'CARGO'
            )
        );
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_obl_generacion_cronograma
ON public.obligacion_financiera (id_generacion_cronograma_financiero)
WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_obl_cronograma_orden
ON public.obligacion_financiera (
    id_relacion_generadora,
    numero_obligacion
)
WHERE deleted_at IS NULL
  AND numero_obligacion IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_obl_cronograma_item_activo
ON public.obligacion_financiera (
    id_relacion_generadora,
    clave_funcional_origen
)
WHERE deleted_at IS NULL
  AND clave_funcional_origen IS NOT NULL;

COMMENT ON COLUMN public.obligacion_financiera.id_generacion_cronograma_financiero IS
'Corrida tecnica que genero o migro este item de cronograma financiero.';

COMMENT ON COLUMN public.obligacion_financiera.numero_obligacion IS
'Orden funcional del item dentro del cronograma financiero.';

COMMENT ON COLUMN public.obligacion_financiera.tipo_item_cronograma IS
'Tipo funcional del item de cronograma: ANTICIPO, CUOTA, SALDO, REFUERZO, AJUSTE o CARGO.';

COMMENT ON COLUMN public.obligacion_financiera.etiqueta_obligacion IS
'Etiqueta estable para UI/reportes del item de cronograma.';

COMMENT ON COLUMN public.obligacion_financiera.clave_funcional_origen IS
'Clave funcional idempotente del item de cronograma. Debe tratarse como estable/inmutable a nivel de aplicacion.';
