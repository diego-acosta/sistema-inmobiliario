-- Patch idempotente: soporte fisico de INDEXACION por bloque en Plan Pago V2.
--
-- Alcance:
-- - Agrega configuracion 1:1 opcional de indexacion para plan_pago_venta_bloque.
-- - Agrega trazabilidad tecnica del indice aplicado por obligacion financiera.
-- - No implementa calculo, preview/generate, endpoints, pagos, caja ni recibos.
-- - INDEXACION queda habilitado fisicamente como metodo_liquidacion de bloque/tramo,
--   no como metodo_plan_pago global.

CREATE TABLE IF NOT EXISTS public.plan_pago_venta_bloque_indexacion (
    id_plan_pago_venta_bloque_indexacion BIGSERIAL PRIMARY KEY,
    uid_global UUID NOT NULL DEFAULT gen_random_uuid(),
    version_registro INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP NULL,
    id_instalacion_origen BIGINT NULL,
    id_instalacion_ultima_modificacion BIGINT NULL,
    op_id_alta UUID NULL,
    op_id_ultima_modificacion UUID NULL,
    id_plan_pago_venta_bloque BIGINT NOT NULL,
    id_indice_financiero BIGINT NOT NULL,
    fecha_base_indice DATE NOT NULL,
    valor_base_indice NUMERIC(18,8) NOT NULL,
    modo_indexacion VARCHAR(40) NOT NULL,
    base_calculo_indexacion VARCHAR(60) NOT NULL,
    tipo_generacion_indexada VARCHAR(40) NOT NULL,
    politica_valor_no_disponible VARCHAR(60) NOT NULL,
    conserva_capital_original BOOLEAN NOT NULL DEFAULT TRUE,
    genera_ajuste_por_diferencia BOOLEAN NOT NULL DEFAULT TRUE,
    observaciones TEXT NULL
);

CREATE TABLE IF NOT EXISTS public.obligacion_financiera_indexacion (
    id_obligacion_financiera_indexacion BIGSERIAL PRIMARY KEY,
    uid_global UUID NOT NULL DEFAULT gen_random_uuid(),
    version_registro INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP NULL,
    id_instalacion_origen BIGINT NULL,
    id_instalacion_ultima_modificacion BIGINT NULL,
    op_id_alta UUID NULL,
    op_id_ultima_modificacion UUID NULL,
    id_obligacion_financiera BIGINT NOT NULL,
    id_plan_pago_venta_bloque_indexacion BIGINT NOT NULL,
    id_indice_financiero BIGINT NOT NULL,
    id_indice_financiero_valor BIGINT NOT NULL,
    fecha_base_indice DATE NOT NULL,
    valor_base_indice NUMERIC(18,8) NOT NULL,
    fecha_aplicacion_indice DATE NOT NULL,
    valor_aplicado_indice NUMERIC(18,8) NOT NULL,
    coeficiente_indexacion NUMERIC(18,8) NOT NULL,
    modo_indexacion VARCHAR(40) NOT NULL,
    base_calculo_indexacion VARCHAR(60) NOT NULL,
    tipo_generacion_indexada VARCHAR(40) NOT NULL,
    observaciones TEXT NULL
);

DO $$
DECLARE
    v_definition TEXT;
BEGIN
    SELECT pg_get_constraintdef(oid)
      INTO v_definition
      FROM pg_constraint
     WHERE conname = 'chk_ppvb_metodo_liquidacion'
       AND conrelid = 'public.plan_pago_venta_bloque'::regclass;

    IF v_definition IS NOT NULL
       AND v_definition NOT LIKE '%INDEXACION%'
    THEN
        ALTER TABLE public.plan_pago_venta_bloque
            DROP CONSTRAINT chk_ppvb_metodo_liquidacion;
    END IF;

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
                OR metodo_liquidacion IN ('SIN_INTERES', 'INTERES_DIRECTO', 'INDEXACION')
            );
    END IF;

    IF NOT EXISTS (
        SELECT 1
          FROM pg_constraint
         WHERE conname = 'uq_ppvbi_uid_global'
           AND conrelid = 'public.plan_pago_venta_bloque_indexacion'::regclass
    ) THEN
        ALTER TABLE public.plan_pago_venta_bloque_indexacion
            ADD CONSTRAINT uq_ppvbi_uid_global UNIQUE (uid_global);
    END IF;

    IF NOT EXISTS (
        SELECT 1
          FROM pg_constraint
         WHERE conname = 'uq_indice_financiero_valor_id_indice_pair'
           AND conrelid = 'public.indice_financiero_valor'::regclass
    ) THEN
        ALTER TABLE public.indice_financiero_valor
            ADD CONSTRAINT uq_indice_financiero_valor_id_indice_pair
            UNIQUE (id_indice_financiero_valor, id_indice_financiero);
    END IF;

    IF NOT EXISTS (
        SELECT 1
          FROM pg_constraint
         WHERE conname = 'fk_ppvbi_plan_pago_venta_bloque'
           AND conrelid = 'public.plan_pago_venta_bloque_indexacion'::regclass
    ) THEN
        ALTER TABLE public.plan_pago_venta_bloque_indexacion
            ADD CONSTRAINT fk_ppvbi_plan_pago_venta_bloque
            FOREIGN KEY (id_plan_pago_venta_bloque)
            REFERENCES public.plan_pago_venta_bloque (id_plan_pago_venta_bloque)
            ON DELETE RESTRICT;
    END IF;

    IF NOT EXISTS (
        SELECT 1
          FROM pg_constraint
         WHERE conname = 'fk_ppvbi_indice_financiero'
           AND conrelid = 'public.plan_pago_venta_bloque_indexacion'::regclass
    ) THEN
        ALTER TABLE public.plan_pago_venta_bloque_indexacion
            ADD CONSTRAINT fk_ppvbi_indice_financiero
            FOREIGN KEY (id_indice_financiero)
            REFERENCES public.indice_financiero (id_indice_financiero)
            ON DELETE RESTRICT;
    END IF;

    IF NOT EXISTS (
        SELECT 1
          FROM pg_constraint
         WHERE conname = 'uq_ppvbi_id_indice_pair'
           AND conrelid = 'public.plan_pago_venta_bloque_indexacion'::regclass
    ) THEN
        ALTER TABLE public.plan_pago_venta_bloque_indexacion
            ADD CONSTRAINT uq_ppvbi_id_indice_pair
            UNIQUE (id_plan_pago_venta_bloque_indexacion, id_indice_financiero);
    END IF;

    IF NOT EXISTS (
        SELECT 1
          FROM pg_constraint
         WHERE conname = 'ck_ppvbi_deleted_at'
           AND conrelid = 'public.plan_pago_venta_bloque_indexacion'::regclass
    ) THEN
        ALTER TABLE public.plan_pago_venta_bloque_indexacion
            ADD CONSTRAINT ck_ppvbi_deleted_at
            CHECK (deleted_at IS NULL OR deleted_at >= created_at);
    END IF;

    IF NOT EXISTS (
        SELECT 1
          FROM pg_constraint
         WHERE conname = 'ck_ppvbi_valor_base_indice_positivo'
           AND conrelid = 'public.plan_pago_venta_bloque_indexacion'::regclass
    ) THEN
        ALTER TABLE public.plan_pago_venta_bloque_indexacion
            ADD CONSTRAINT ck_ppvbi_valor_base_indice_positivo
            CHECK (valor_base_indice > 0);
    END IF;

    IF NOT EXISTS (
        SELECT 1
          FROM pg_constraint
         WHERE conname = 'ck_ppvbi_modo_indexacion'
           AND conrelid = 'public.plan_pago_venta_bloque_indexacion'::regclass
    ) THEN
        ALTER TABLE public.plan_pago_venta_bloque_indexacion
            ADD CONSTRAINT ck_ppvbi_modo_indexacion
            CHECK (modo_indexacion IN ('POR_COEFICIENTE'));
    END IF;

    IF NOT EXISTS (
        SELECT 1
          FROM pg_constraint
         WHERE conname = 'ck_ppvbi_base_calculo_indexacion'
           AND conrelid = 'public.plan_pago_venta_bloque_indexacion'::regclass
    ) THEN
        ALTER TABLE public.plan_pago_venta_bloque_indexacion
            ADD CONSTRAINT ck_ppvbi_base_calculo_indexacion
            CHECK (base_calculo_indexacion IN ('CAPITAL_INICIAL_BLOQUE'));
    END IF;

    IF NOT EXISTS (
        SELECT 1
          FROM pg_constraint
         WHERE conname = 'ck_ppvbi_tipo_generacion_indexada'
           AND conrelid = 'public.plan_pago_venta_bloque_indexacion'::regclass
    ) THEN
        ALTER TABLE public.plan_pago_venta_bloque_indexacion
            ADD CONSTRAINT ck_ppvbi_tipo_generacion_indexada
            CHECK (tipo_generacion_indexada IN ('DEFINITIVA'));
    END IF;

    IF NOT EXISTS (
        SELECT 1
          FROM pg_constraint
         WHERE conname = 'ck_ppvbi_politica_valor_no_disponible'
           AND conrelid = 'public.plan_pago_venta_bloque_indexacion'::regclass
    ) THEN
        ALTER TABLE public.plan_pago_venta_bloque_indexacion
            ADD CONSTRAINT ck_ppvbi_politica_valor_no_disponible
            CHECK (politica_valor_no_disponible IN ('ERROR_SI_NO_EXISTE'));
    END IF;

    IF NOT EXISTS (
        SELECT 1
          FROM pg_constraint
         WHERE conname = 'ck_ppvbi_conserva_capital_original'
           AND conrelid = 'public.plan_pago_venta_bloque_indexacion'::regclass
    ) THEN
        ALTER TABLE public.plan_pago_venta_bloque_indexacion
            ADD CONSTRAINT ck_ppvbi_conserva_capital_original
            CHECK (conserva_capital_original = TRUE);
    END IF;

    IF NOT EXISTS (
        SELECT 1
          FROM pg_constraint
         WHERE conname = 'ck_ppvbi_genera_ajuste_por_diferencia'
           AND conrelid = 'public.plan_pago_venta_bloque_indexacion'::regclass
    ) THEN
        ALTER TABLE public.plan_pago_venta_bloque_indexacion
            ADD CONSTRAINT ck_ppvbi_genera_ajuste_por_diferencia
            CHECK (genera_ajuste_por_diferencia = TRUE);
    END IF;

    IF NOT EXISTS (
        SELECT 1
          FROM pg_constraint
         WHERE conname = 'uq_ofi_uid_global'
           AND conrelid = 'public.obligacion_financiera_indexacion'::regclass
    ) THEN
        ALTER TABLE public.obligacion_financiera_indexacion
            ADD CONSTRAINT uq_ofi_uid_global UNIQUE (uid_global);
    END IF;

    IF NOT EXISTS (
        SELECT 1
          FROM pg_constraint
         WHERE conname = 'fk_ofi_obligacion_financiera'
           AND conrelid = 'public.obligacion_financiera_indexacion'::regclass
    ) THEN
        ALTER TABLE public.obligacion_financiera_indexacion
            ADD CONSTRAINT fk_ofi_obligacion_financiera
            FOREIGN KEY (id_obligacion_financiera)
            REFERENCES public.obligacion_financiera (id_obligacion_financiera)
            ON DELETE RESTRICT;
    END IF;

    IF NOT EXISTS (
        SELECT 1
          FROM pg_constraint
         WHERE conname = 'fk_ofi_plan_pago_venta_bloque_indexacion'
           AND conrelid = 'public.obligacion_financiera_indexacion'::regclass
    ) THEN
        ALTER TABLE public.obligacion_financiera_indexacion
            ADD CONSTRAINT fk_ofi_plan_pago_venta_bloque_indexacion
            FOREIGN KEY (id_plan_pago_venta_bloque_indexacion)
            REFERENCES public.plan_pago_venta_bloque_indexacion (id_plan_pago_venta_bloque_indexacion)
            ON DELETE RESTRICT;
    END IF;

    IF NOT EXISTS (
        SELECT 1
          FROM pg_constraint
         WHERE conname = 'fk_ofi_indice_financiero'
           AND conrelid = 'public.obligacion_financiera_indexacion'::regclass
    ) THEN
        ALTER TABLE public.obligacion_financiera_indexacion
            ADD CONSTRAINT fk_ofi_indice_financiero
            FOREIGN KEY (id_indice_financiero)
            REFERENCES public.indice_financiero (id_indice_financiero)
            ON DELETE RESTRICT;
    END IF;

    IF NOT EXISTS (
        SELECT 1
          FROM pg_constraint
         WHERE conname = 'fk_ofi_indice_financiero_valor'
           AND conrelid = 'public.obligacion_financiera_indexacion'::regclass
    ) THEN
        ALTER TABLE public.obligacion_financiera_indexacion
            ADD CONSTRAINT fk_ofi_indice_financiero_valor
            FOREIGN KEY (id_indice_financiero_valor)
            REFERENCES public.indice_financiero_valor (id_indice_financiero_valor)
            ON DELETE RESTRICT;
    END IF;

    IF NOT EXISTS (
        SELECT 1
          FROM pg_constraint
         WHERE conname = 'fk_ofi_indice_financiero_valor_mismo_indice'
           AND conrelid = 'public.obligacion_financiera_indexacion'::regclass
    ) THEN
        ALTER TABLE public.obligacion_financiera_indexacion
            ADD CONSTRAINT fk_ofi_indice_financiero_valor_mismo_indice
            FOREIGN KEY (id_indice_financiero_valor, id_indice_financiero)
            REFERENCES public.indice_financiero_valor (id_indice_financiero_valor, id_indice_financiero)
            ON DELETE RESTRICT;
    END IF;

    IF NOT EXISTS (
        SELECT 1
          FROM pg_constraint
         WHERE conname = 'fk_ofi_bloque_indexacion_mismo_indice'
           AND conrelid = 'public.obligacion_financiera_indexacion'::regclass
    ) THEN
        ALTER TABLE public.obligacion_financiera_indexacion
            ADD CONSTRAINT fk_ofi_bloque_indexacion_mismo_indice
            FOREIGN KEY (id_plan_pago_venta_bloque_indexacion, id_indice_financiero)
            REFERENCES public.plan_pago_venta_bloque_indexacion (id_plan_pago_venta_bloque_indexacion, id_indice_financiero)
            ON DELETE RESTRICT;
    END IF;

    IF NOT EXISTS (
        SELECT 1
          FROM pg_constraint
         WHERE conname = 'ck_ofi_deleted_at'
           AND conrelid = 'public.obligacion_financiera_indexacion'::regclass
    ) THEN
        ALTER TABLE public.obligacion_financiera_indexacion
            ADD CONSTRAINT ck_ofi_deleted_at
            CHECK (deleted_at IS NULL OR deleted_at >= created_at);
    END IF;

    IF NOT EXISTS (
        SELECT 1
          FROM pg_constraint
         WHERE conname = 'ck_ofi_valor_base_indice_positivo'
           AND conrelid = 'public.obligacion_financiera_indexacion'::regclass
    ) THEN
        ALTER TABLE public.obligacion_financiera_indexacion
            ADD CONSTRAINT ck_ofi_valor_base_indice_positivo
            CHECK (valor_base_indice > 0);
    END IF;

    IF NOT EXISTS (
        SELECT 1
          FROM pg_constraint
         WHERE conname = 'ck_ofi_valor_aplicado_indice_positivo'
           AND conrelid = 'public.obligacion_financiera_indexacion'::regclass
    ) THEN
        ALTER TABLE public.obligacion_financiera_indexacion
            ADD CONSTRAINT ck_ofi_valor_aplicado_indice_positivo
            CHECK (valor_aplicado_indice > 0);
    END IF;

    IF NOT EXISTS (
        SELECT 1
          FROM pg_constraint
         WHERE conname = 'ck_ofi_coeficiente_indexacion_positivo'
           AND conrelid = 'public.obligacion_financiera_indexacion'::regclass
    ) THEN
        ALTER TABLE public.obligacion_financiera_indexacion
            ADD CONSTRAINT ck_ofi_coeficiente_indexacion_positivo
            CHECK (coeficiente_indexacion > 0);
    END IF;

    IF NOT EXISTS (
        SELECT 1
          FROM pg_constraint
         WHERE conname = 'ck_ofi_modo_indexacion'
           AND conrelid = 'public.obligacion_financiera_indexacion'::regclass
    ) THEN
        ALTER TABLE public.obligacion_financiera_indexacion
            ADD CONSTRAINT ck_ofi_modo_indexacion
            CHECK (modo_indexacion IN ('POR_COEFICIENTE'));
    END IF;

    IF NOT EXISTS (
        SELECT 1
          FROM pg_constraint
         WHERE conname = 'ck_ofi_base_calculo_indexacion'
           AND conrelid = 'public.obligacion_financiera_indexacion'::regclass
    ) THEN
        ALTER TABLE public.obligacion_financiera_indexacion
            ADD CONSTRAINT ck_ofi_base_calculo_indexacion
            CHECK (base_calculo_indexacion IN ('CAPITAL_INICIAL_BLOQUE'));
    END IF;

    IF NOT EXISTS (
        SELECT 1
          FROM pg_constraint
         WHERE conname = 'ck_ofi_tipo_generacion_indexada'
           AND conrelid = 'public.obligacion_financiera_indexacion'::regclass
    ) THEN
        ALTER TABLE public.obligacion_financiera_indexacion
            ADD CONSTRAINT ck_ofi_tipo_generacion_indexada
            CHECK (tipo_generacion_indexada IN ('DEFINITIVA'));
    END IF;
END
$$;

CREATE INDEX IF NOT EXISTS idx_ppvbi_uid_global
    ON public.plan_pago_venta_bloque_indexacion (uid_global);

CREATE UNIQUE INDEX IF NOT EXISTS idx_ppvbi_bloque_activo
    ON public.plan_pago_venta_bloque_indexacion (id_plan_pago_venta_bloque)
    WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_ppvbi_indice_activo
    ON public.plan_pago_venta_bloque_indexacion (id_indice_financiero)
    WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_ofi_uid_global
    ON public.obligacion_financiera_indexacion (uid_global);

CREATE UNIQUE INDEX IF NOT EXISTS idx_ofi_obligacion_activo
    ON public.obligacion_financiera_indexacion (id_obligacion_financiera)
    WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_ofi_bloque_indexacion_activo
    ON public.obligacion_financiera_indexacion (id_plan_pago_venta_bloque_indexacion)
    WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_ofi_indice_valor_activo
    ON public.obligacion_financiera_indexacion (id_indice_financiero_valor)
    WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_ofi_fecha_aplicacion_activo
    ON public.obligacion_financiera_indexacion (fecha_aplicacion_indice)
    WHERE deleted_at IS NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_trigger
        WHERE tgname = 'trg_bi_ppvbi_core_ef'
          AND tgrelid = 'public.plan_pago_venta_bloque_indexacion'::regclass
    ) THEN
        CREATE TRIGGER trg_bi_ppvbi_core_ef
        BEFORE INSERT ON public.plan_pago_venta_bloque_indexacion
        FOR EACH ROW EXECUTE FUNCTION public.trg_core_ef_sync_defaults_insert();
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_trigger
        WHERE tgname = 'trg_bu_ppvbi_core_ef'
          AND tgrelid = 'public.plan_pago_venta_bloque_indexacion'::regclass
    ) THEN
        CREATE TRIGGER trg_bu_ppvbi_core_ef
        BEFORE UPDATE ON public.plan_pago_venta_bloque_indexacion
        FOR EACH ROW EXECUTE FUNCTION public.trg_core_ef_sync_defaults_update();
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_trigger
        WHERE tgname = 'trg_bi_ofi_core_ef'
          AND tgrelid = 'public.obligacion_financiera_indexacion'::regclass
    ) THEN
        CREATE TRIGGER trg_bi_ofi_core_ef
        BEFORE INSERT ON public.obligacion_financiera_indexacion
        FOR EACH ROW EXECUTE FUNCTION public.trg_core_ef_sync_defaults_insert();
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_trigger
        WHERE tgname = 'trg_bu_ofi_core_ef'
          AND tgrelid = 'public.obligacion_financiera_indexacion'::regclass
    ) THEN
        CREATE TRIGGER trg_bu_ofi_core_ef
        BEFORE UPDATE ON public.obligacion_financiera_indexacion
        FOR EACH ROW EXECUTE FUNCTION public.trg_core_ef_sync_defaults_update();
    END IF;
END $$;

COMMENT ON TABLE public.plan_pago_venta_bloque_indexacion IS
    'Configuracion de INDEXACION para un bloque/tramo de Plan Pago V2. No representa deuda, obligacion ni importe final de cuotas.';
COMMENT ON COLUMN public.plan_pago_venta_bloque_indexacion.id_plan_pago_venta_bloque IS
    'Bloque comercial configurado para INDEXACION; INDEXACION es metodo_liquidacion del bloque, no metodo_plan_pago global.';
COMMENT ON COLUMN public.plan_pago_venta_bloque_indexacion.valor_base_indice IS
    'Valor base del indice para configurar el bloque. El valor aplicado puede variar por obligacion/cuota segun fecha de vencimiento.';
COMMENT ON COLUMN public.plan_pago_venta_bloque_indexacion.conserva_capital_original IS
    'En esta etapa debe ser TRUE: CAPITAL_VENTA debe vivir en composicion_obligacion cuando se implemente generate.';
COMMENT ON COLUMN public.plan_pago_venta_bloque_indexacion.genera_ajuste_por_diferencia IS
    'En esta etapa debe ser TRUE: AJUSTE_INDEXACION debe vivir en composicion_obligacion cuando se implemente generate.';

COMMENT ON TABLE public.obligacion_financiera_indexacion IS
    'Trazabilidad tecnica del indice aplicado a una obligacion financiera. No duplica importes, saldos, capitales ni moneda.';
COMMENT ON COLUMN public.obligacion_financiera_indexacion.id_obligacion_financiera IS
    'Obligacion cuya indexacion queda trazada; importe_total, saldo, moneda, estado y vencimiento viven en obligacion_financiera.';
COMMENT ON COLUMN public.obligacion_financiera_indexacion.id_indice_financiero_valor IS
    'Valor de indice congelado/aplicado para trazabilidad tecnica de la obligacion indexada; debe pertenecer al mismo id_indice_financiero trazado.';
COMMENT ON COLUMN public.obligacion_financiera_indexacion.coeficiente_indexacion IS
    'Coeficiente tecnico usado para explicar el calculo indexado; los importes resultantes no se duplican en esta tabla.';
COMMENT ON COLUMN public.obligacion_financiera_indexacion.id_plan_pago_venta_bloque_indexacion IS
    'Configuracion de bloque indexado asociada; debe compartir el mismo id_indice_financiero trazado en la obligacion.';
COMMENT ON COLUMN public.obligacion_financiera_indexacion.base_calculo_indexacion IS
    'Base tecnica de calculo. CAPITAL_VENTA y AJUSTE_INDEXACION deben materializarse en composicion_obligacion cuando se implemente generate.';
