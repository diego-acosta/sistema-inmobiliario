-- Patch idempotente: infraestructura SQL base para corridas de indexacion financiera V2.
-- Alcance: solo persistencia e integridad estructural de cabecera y detalle.
-- No implementa preview, aplicacion, locks funcionales, jobs, importador ni reversión.

CREATE TABLE IF NOT EXISTS public.corrida_indexacion_financiera (
    id_corrida_indexacion_financiera BIGSERIAL PRIMARY KEY,
    uid_global UUID NOT NULL DEFAULT gen_random_uuid(),
    version_registro INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP NULL,
    id_instalacion_origen BIGINT NULL,
    id_instalacion_ultima_modificacion BIGINT NULL,
    op_id_alta UUID NULL,
    op_id_ultima_modificacion UUID NULL,

    id_plan_pago_venta BIGINT NOT NULL,
    id_plan_pago_venta_bloque BIGINT NOT NULL,
    id_plan_pago_venta_bloque_indexacion BIGINT NULL,
    id_generacion_cronograma_financiero BIGINT NULL,
    id_indice_financiero BIGINT NOT NULL,
    id_indice_financiero_valor_base BIGINT NULL,
    id_indice_financiero_valor_aplicado BIGINT NOT NULL,

    periodo_base DATE NULL,
    periodo_aplicado DATE NOT NULL,
    fecha_corte DATE NOT NULL,
    fecha_calculo TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_publicacion_indice DATE NULL,
    fecha_aplicacion TIMESTAMP NULL,

    origen_corrida VARCHAR(50) NOT NULL,
    estado_corrida VARCHAR(30) NOT NULL DEFAULT 'BORRADOR',
    op_id UUID NOT NULL,
    hash_corrida VARCHAR(128) NOT NULL,
    payload_hash VARCHAR(128) NULL,
    snapshot_alcance JSONB NULL,
    snapshot_versiones JSONB NULL,

    id_usuario BIGINT NULL,
    id_sucursal BIGINT NULL,
    origen_tecnico VARCHAR(80) NULL,
    referencia_lote VARCHAR(120) NULL,
    referencia_importacion VARCHAR(120) NULL,
    referencia_job VARCHAR(120) NULL,
    motivo TEXT NULL,
    observaciones TEXT NULL,
    codigo_error VARCHAR(80) NULL,
    etapa_error VARCHAR(80) NULL,
    diagnostico_tecnico TEXT NULL,

    cantidad_analizada INTEGER NOT NULL DEFAULT 0,
    cantidad_elegible INTEGER NOT NULL DEFAULT 0,
    cantidad_excluida INTEGER NOT NULL DEFAULT 0,
    cantidad_aplicada INTEGER NOT NULL DEFAULT 0,
    importe_total_anterior NUMERIC(14,2) NOT NULL DEFAULT 0,
    importe_total_nuevo NUMERIC(14,2) NOT NULL DEFAULT 0,
    ajuste_anterior_total NUMERIC(14,2) NOT NULL DEFAULT 0,
    ajuste_nuevo_total NUMERIC(14,2) NOT NULL DEFAULT 0,
    saldo_anterior_total NUMERIC(14,2) NOT NULL DEFAULT 0,
    saldo_nuevo_total NUMERIC(14,2) NOT NULL DEFAULT 0,

    id_corrida_anterior BIGINT NULL,
    id_corrida_reemplazante BIGINT NULL
);

CREATE TABLE IF NOT EXISTS public.corrida_indexacion_financiera_detalle (
    id_corrida_indexacion_financiera_detalle BIGSERIAL PRIMARY KEY,
    uid_global UUID NOT NULL DEFAULT gen_random_uuid(),
    version_registro INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP NULL,
    id_instalacion_origen BIGINT NULL,
    id_instalacion_ultima_modificacion BIGINT NULL,
    op_id_alta UUID NULL,
    op_id_ultima_modificacion UUID NULL,

    id_corrida_indexacion_financiera BIGINT NOT NULL,
    id_obligacion_financiera BIGINT NOT NULL,
    id_composicion_capital_venta BIGINT NULL,
    id_composicion_ajuste_indexacion BIGINT NULL,
    id_obligacion_financiera_indexacion BIGINT NULL,

    version_esperada INTEGER NOT NULL,
    version_resultante INTEGER NULL,

    capital_base NUMERIC(14,2) NOT NULL DEFAULT 0,
    valor_indice_base NUMERIC(18,8) NOT NULL,
    valor_indice_aplicado NUMERIC(18,8) NOT NULL,
    coeficiente_indexacion NUMERIC(18,8) NOT NULL,
    ajuste_anterior NUMERIC(14,2) NOT NULL DEFAULT 0,
    ajuste_nuevo NUMERIC(14,2) NOT NULL DEFAULT 0,
    diferencia_neta NUMERIC(14,2) NOT NULL DEFAULT 0,
    importe_anterior NUMERIC(14,2) NOT NULL DEFAULT 0,
    importe_nuevo NUMERIC(14,2) NOT NULL DEFAULT 0,
    saldo_anterior NUMERIC(14,2) NOT NULL DEFAULT 0,
    saldo_nuevo NUMERIC(14,2) NOT NULL DEFAULT 0,

    estado_elegibilidad VARCHAR(30) NOT NULL,
    motivo_exclusion TEXT NULL,
    codigo_error VARCHAR(80) NULL,
    detalle_controlado TEXT NULL,
    advertencias JSONB NULL,
    snapshot_antes JSONB NULL,
    snapshot_despues JSONB NULL
);

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_ppvb_id_plan_pair' AND conrelid = 'public.plan_pago_venta_bloque'::regclass) THEN
        ALTER TABLE public.plan_pago_venta_bloque ADD CONSTRAINT uq_ppvb_id_plan_pair UNIQUE (id_plan_pago_venta_bloque, id_plan_pago_venta);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_ifv_id_indice_pair' AND conrelid = 'public.indice_financiero_valor'::regclass) THEN
        ALTER TABLE public.indice_financiero_valor ADD CONSTRAINT uq_ifv_id_indice_pair UNIQUE (id_indice_financiero_valor, id_indice_financiero);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_ppvbi_id_bloque_indice_pair' AND conrelid = 'public.plan_pago_venta_bloque_indexacion'::regclass) THEN
        ALTER TABLE public.plan_pago_venta_bloque_indexacion ADD CONSTRAINT uq_ppvbi_id_bloque_indice_pair UNIQUE (id_plan_pago_venta_bloque_indexacion, id_plan_pago_venta_bloque, id_indice_financiero);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_composicion_obligacion_id_obligacion_pair' AND conrelid = 'public.composicion_obligacion'::regclass) THEN
        ALTER TABLE public.composicion_obligacion ADD CONSTRAINT uq_composicion_obligacion_id_obligacion_pair UNIQUE (id_composicion_obligacion, id_obligacion_financiera);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_ofi_id_obligacion_pair' AND conrelid = 'public.obligacion_financiera_indexacion'::regclass) THEN
        ALTER TABLE public.obligacion_financiera_indexacion ADD CONSTRAINT uq_ofi_id_obligacion_pair UNIQUE (id_obligacion_financiera_indexacion, id_obligacion_financiera);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_gcf_id_plan_pair' AND conrelid = 'public.generacion_cronograma_financiero'::regclass) THEN
        ALTER TABLE public.generacion_cronograma_financiero ADD CONSTRAINT uq_gcf_id_plan_pair UNIQUE (id_generacion_cronograma_financiero, id_plan_pago_venta);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_cif_uid_global' AND conrelid = 'public.corrida_indexacion_financiera'::regclass) THEN
        ALTER TABLE public.corrida_indexacion_financiera ADD CONSTRAINT uq_cif_uid_global UNIQUE (uid_global);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_cifd_uid_global' AND conrelid = 'public.corrida_indexacion_financiera_detalle'::regclass) THEN
        ALTER TABLE public.corrida_indexacion_financiera_detalle ADD CONSTRAINT uq_cifd_uid_global UNIQUE (uid_global);
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_cif_plan_pago_venta' AND conrelid = 'public.corrida_indexacion_financiera'::regclass) THEN
        ALTER TABLE public.corrida_indexacion_financiera ADD CONSTRAINT fk_cif_plan_pago_venta FOREIGN KEY (id_plan_pago_venta) REFERENCES public.plan_pago_venta(id_plan_pago_venta) ON DELETE RESTRICT;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_cif_bloque_mismo_plan' AND conrelid = 'public.corrida_indexacion_financiera'::regclass) THEN
        ALTER TABLE public.corrida_indexacion_financiera ADD CONSTRAINT fk_cif_bloque_mismo_plan FOREIGN KEY (id_plan_pago_venta_bloque, id_plan_pago_venta) REFERENCES public.plan_pago_venta_bloque(id_plan_pago_venta_bloque, id_plan_pago_venta) ON DELETE RESTRICT;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_cif_bloque_indexacion_mismo_bloque_indice' AND conrelid = 'public.corrida_indexacion_financiera'::regclass) THEN
        ALTER TABLE public.corrida_indexacion_financiera ADD CONSTRAINT fk_cif_bloque_indexacion_mismo_bloque_indice FOREIGN KEY (id_plan_pago_venta_bloque_indexacion, id_plan_pago_venta_bloque, id_indice_financiero) REFERENCES public.plan_pago_venta_bloque_indexacion(id_plan_pago_venta_bloque_indexacion, id_plan_pago_venta_bloque, id_indice_financiero) ON DELETE RESTRICT;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_cif_generacion_mismo_plan' AND conrelid = 'public.corrida_indexacion_financiera'::regclass) THEN
        ALTER TABLE public.corrida_indexacion_financiera ADD CONSTRAINT fk_cif_generacion_mismo_plan FOREIGN KEY (id_generacion_cronograma_financiero, id_plan_pago_venta) REFERENCES public.generacion_cronograma_financiero(id_generacion_cronograma_financiero, id_plan_pago_venta) ON DELETE RESTRICT;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_cif_indice_financiero' AND conrelid = 'public.corrida_indexacion_financiera'::regclass) THEN
        ALTER TABLE public.corrida_indexacion_financiera ADD CONSTRAINT fk_cif_indice_financiero FOREIGN KEY (id_indice_financiero) REFERENCES public.indice_financiero(id_indice_financiero) ON DELETE RESTRICT;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_cif_valor_base_mismo_indice' AND conrelid = 'public.corrida_indexacion_financiera'::regclass) THEN
        ALTER TABLE public.corrida_indexacion_financiera ADD CONSTRAINT fk_cif_valor_base_mismo_indice FOREIGN KEY (id_indice_financiero_valor_base, id_indice_financiero) REFERENCES public.indice_financiero_valor(id_indice_financiero_valor, id_indice_financiero) ON DELETE RESTRICT;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_cif_valor_aplicado_mismo_indice' AND conrelid = 'public.corrida_indexacion_financiera'::regclass) THEN
        ALTER TABLE public.corrida_indexacion_financiera ADD CONSTRAINT fk_cif_valor_aplicado_mismo_indice FOREIGN KEY (id_indice_financiero_valor_aplicado, id_indice_financiero) REFERENCES public.indice_financiero_valor(id_indice_financiero_valor, id_indice_financiero) ON DELETE RESTRICT;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_cif_anterior' AND conrelid = 'public.corrida_indexacion_financiera'::regclass) THEN
        ALTER TABLE public.corrida_indexacion_financiera ADD CONSTRAINT fk_cif_anterior FOREIGN KEY (id_corrida_anterior) REFERENCES public.corrida_indexacion_financiera(id_corrida_indexacion_financiera) ON DELETE RESTRICT;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_cif_reemplazante' AND conrelid = 'public.corrida_indexacion_financiera'::regclass) THEN
        ALTER TABLE public.corrida_indexacion_financiera ADD CONSTRAINT fk_cif_reemplazante FOREIGN KEY (id_corrida_reemplazante) REFERENCES public.corrida_indexacion_financiera(id_corrida_indexacion_financiera) ON DELETE RESTRICT;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_cifd_corrida' AND conrelid = 'public.corrida_indexacion_financiera_detalle'::regclass) THEN
        ALTER TABLE public.corrida_indexacion_financiera_detalle ADD CONSTRAINT fk_cifd_corrida FOREIGN KEY (id_corrida_indexacion_financiera) REFERENCES public.corrida_indexacion_financiera(id_corrida_indexacion_financiera) ON DELETE RESTRICT;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_cifd_obligacion' AND conrelid = 'public.corrida_indexacion_financiera_detalle'::regclass) THEN
        ALTER TABLE public.corrida_indexacion_financiera_detalle ADD CONSTRAINT fk_cifd_obligacion FOREIGN KEY (id_obligacion_financiera) REFERENCES public.obligacion_financiera(id_obligacion_financiera) ON DELETE RESTRICT;
    END IF;
    IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_cifd_composicion_capital' AND conrelid = 'public.corrida_indexacion_financiera_detalle'::regclass) THEN
        ALTER TABLE public.corrida_indexacion_financiera_detalle DROP CONSTRAINT fk_cifd_composicion_capital;
    END IF;
    IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_cifd_composicion_ajuste' AND conrelid = 'public.corrida_indexacion_financiera_detalle'::regclass) THEN
        ALTER TABLE public.corrida_indexacion_financiera_detalle DROP CONSTRAINT fk_cifd_composicion_ajuste;
    END IF;
    IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_cifd_obligacion_indexacion' AND conrelid = 'public.corrida_indexacion_financiera_detalle'::regclass) THEN
        ALTER TABLE public.corrida_indexacion_financiera_detalle DROP CONSTRAINT fk_cifd_obligacion_indexacion;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_cifd_composicion_capital_obligacion' AND conrelid = 'public.corrida_indexacion_financiera_detalle'::regclass) THEN
        ALTER TABLE public.corrida_indexacion_financiera_detalle ADD CONSTRAINT fk_cifd_composicion_capital_obligacion FOREIGN KEY (id_composicion_capital_venta, id_obligacion_financiera) REFERENCES public.composicion_obligacion(id_composicion_obligacion, id_obligacion_financiera) ON DELETE RESTRICT;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_cifd_composicion_ajuste_obligacion' AND conrelid = 'public.corrida_indexacion_financiera_detalle'::regclass) THEN
        ALTER TABLE public.corrida_indexacion_financiera_detalle ADD CONSTRAINT fk_cifd_composicion_ajuste_obligacion FOREIGN KEY (id_composicion_ajuste_indexacion, id_obligacion_financiera) REFERENCES public.composicion_obligacion(id_composicion_obligacion, id_obligacion_financiera) ON DELETE RESTRICT;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_cifd_obligacion_indexacion_obligacion' AND conrelid = 'public.corrida_indexacion_financiera_detalle'::regclass) THEN
        ALTER TABLE public.corrida_indexacion_financiera_detalle ADD CONSTRAINT fk_cifd_obligacion_indexacion_obligacion FOREIGN KEY (id_obligacion_financiera_indexacion, id_obligacion_financiera) REFERENCES public.obligacion_financiera_indexacion(id_obligacion_financiera_indexacion, id_obligacion_financiera) ON DELETE RESTRICT;
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_cif_estado' AND conrelid = 'public.corrida_indexacion_financiera'::regclass) THEN
        ALTER TABLE public.corrida_indexacion_financiera ADD CONSTRAINT ck_cif_estado CHECK (estado_corrida IN ('BORRADOR','PREVISUALIZADA','PENDIENTE_APLICACION','APLICADA','FALLIDA','ANULADA','REEMPLAZADA'));
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_cif_origen' AND conrelid = 'public.corrida_indexacion_financiera'::regclass) THEN
        ALTER TABLE public.corrida_indexacion_financiera ADD CONSTRAINT ck_cif_origen CHECK (origen_corrida IN ('IMPORTACION_VENTA_HISTORICA','ALTA_MANUAL_VENTA_HISTORICA','PUBLICACION_INDICE','REINDEXACION_MANUAL','CORRECCION_INDICE','REPROCESO_CONTROLADO'));
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_cif_cantidades_no_negativas' AND conrelid = 'public.corrida_indexacion_financiera'::regclass) THEN
        ALTER TABLE public.corrida_indexacion_financiera ADD CONSTRAINT ck_cif_cantidades_no_negativas CHECK (cantidad_analizada >= 0 AND cantidad_elegible >= 0 AND cantidad_excluida >= 0 AND cantidad_aplicada >= 0 AND cantidad_elegible + cantidad_excluida <= cantidad_analizada AND cantidad_aplicada <= cantidad_elegible);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_cif_importes_no_negativos' AND conrelid = 'public.corrida_indexacion_financiera'::regclass) THEN
        ALTER TABLE public.corrida_indexacion_financiera ADD CONSTRAINT ck_cif_importes_no_negativos CHECK (importe_total_anterior >= 0 AND importe_total_nuevo >= 0 AND ajuste_anterior_total >= 0 AND ajuste_nuevo_total >= 0 AND saldo_anterior_total >= 0 AND saldo_nuevo_total >= 0);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_cif_fechas' AND conrelid = 'public.corrida_indexacion_financiera'::regclass) THEN
        ALTER TABLE public.corrida_indexacion_financiera ADD CONSTRAINT ck_cif_fechas CHECK ((periodo_base IS NULL OR periodo_aplicado >= periodo_base) AND fecha_corte <= fecha_calculo::date AND (fecha_publicacion_indice IS NULL OR fecha_publicacion_indice <= fecha_calculo::date));
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_cif_fecha_aplicacion_estado' AND conrelid = 'public.corrida_indexacion_financiera'::regclass) THEN
        ALTER TABLE public.corrida_indexacion_financiera ADD CONSTRAINT ck_cif_fecha_aplicacion_estado CHECK ((estado_corrida = 'APLICADA' AND fecha_aplicacion IS NOT NULL) OR (estado_corrida <> 'APLICADA' AND fecha_aplicacion IS NULL));
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_cif_error_estado' AND conrelid = 'public.corrida_indexacion_financiera'::regclass) THEN
        ALTER TABLE public.corrida_indexacion_financiera ADD CONSTRAINT ck_cif_error_estado CHECK ((codigo_error IS NULL AND etapa_error IS NULL AND diagnostico_tecnico IS NULL) OR estado_corrida = 'FALLIDA');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_cif_reemplazo_no_autoref' AND conrelid = 'public.corrida_indexacion_financiera'::regclass) THEN
        ALTER TABLE public.corrida_indexacion_financiera ADD CONSTRAINT ck_cif_reemplazo_no_autoref CHECK ((id_corrida_anterior IS NULL OR id_corrida_anterior <> id_corrida_indexacion_financiera) AND (id_corrida_reemplazante IS NULL OR id_corrida_reemplazante <> id_corrida_indexacion_financiera) AND (id_corrida_anterior IS NULL OR id_corrida_reemplazante IS NULL OR id_corrida_anterior <> id_corrida_reemplazante));
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_cifd_versiones' AND conrelid = 'public.corrida_indexacion_financiera_detalle'::regclass) THEN
        ALTER TABLE public.corrida_indexacion_financiera_detalle ADD CONSTRAINT ck_cifd_versiones CHECK (version_esperada > 0 AND (version_resultante IS NULL OR version_resultante > 0));
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_cifd_elegibilidad' AND conrelid = 'public.corrida_indexacion_financiera_detalle'::regclass) THEN
        ALTER TABLE public.corrida_indexacion_financiera_detalle ADD CONSTRAINT ck_cifd_elegibilidad CHECK (estado_elegibilidad IN ('ELEGIBLE','EXCLUIDA','BLOQUEANTE','RESERVADA_FUTURA'));
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_cifd_importes_no_negativos' AND conrelid = 'public.corrida_indexacion_financiera_detalle'::regclass) THEN
        ALTER TABLE public.corrida_indexacion_financiera_detalle ADD CONSTRAINT ck_cifd_importes_no_negativos CHECK (capital_base >= 0 AND valor_indice_base > 0 AND valor_indice_aplicado > 0 AND coeficiente_indexacion > 0 AND ajuste_anterior >= 0 AND ajuste_nuevo >= 0 AND importe_anterior >= 0 AND importe_nuevo >= 0 AND saldo_anterior >= 0 AND saldo_nuevo >= 0);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_cifd_exclusion_motivo' AND conrelid = 'public.corrida_indexacion_financiera_detalle'::regclass) THEN
        ALTER TABLE public.corrida_indexacion_financiera_detalle ADD CONSTRAINT ck_cifd_exclusion_motivo CHECK (estado_elegibilidad <> 'EXCLUIDA' OR motivo_exclusion IS NOT NULL OR codigo_error IS NOT NULL);
    END IF;
END $$;

CREATE UNIQUE INDEX IF NOT EXISTS ux_cif_idempotencia_funcional_activa
    ON public.corrida_indexacion_financiera (id_plan_pago_venta, id_plan_pago_venta_bloque, id_indice_financiero, id_indice_financiero_valor_aplicado, fecha_corte, origen_corrida, hash_corrida)
    WHERE deleted_at IS NULL AND estado_corrida NOT IN ('ANULADA','REEMPLAZADA');
CREATE UNIQUE INDEX IF NOT EXISTS ux_cifd_corrida_obligacion
    ON public.corrida_indexacion_financiera_detalle (id_corrida_indexacion_financiera, id_obligacion_financiera);

CREATE INDEX IF NOT EXISTS idx_cif_version_registro ON public.corrida_indexacion_financiera (version_registro);
CREATE INDEX IF NOT EXISTS idx_cif_timestamps ON public.corrida_indexacion_financiera (created_at, updated_at, deleted_at);
CREATE INDEX IF NOT EXISTS idx_cif_op_ids ON public.corrida_indexacion_financiera (op_id_alta, op_id_ultima_modificacion, op_id);
CREATE INDEX IF NOT EXISTS idx_cif_plan ON public.corrida_indexacion_financiera (id_plan_pago_venta);
CREATE INDEX IF NOT EXISTS idx_cif_bloque ON public.corrida_indexacion_financiera (id_plan_pago_venta_bloque);
CREATE INDEX IF NOT EXISTS idx_cif_plan_bloque ON public.corrida_indexacion_financiera (id_plan_pago_venta, id_plan_pago_venta_bloque);
CREATE INDEX IF NOT EXISTS idx_cif_indice ON public.corrida_indexacion_financiera (id_indice_financiero);
CREATE INDEX IF NOT EXISTS idx_cif_valor_aplicado ON public.corrida_indexacion_financiera (id_indice_financiero_valor_aplicado);
CREATE INDEX IF NOT EXISTS idx_cif_estado ON public.corrida_indexacion_financiera (estado_corrida);
CREATE INDEX IF NOT EXISTS idx_cif_origen ON public.corrida_indexacion_financiera (origen_corrida);
CREATE INDEX IF NOT EXISTS idx_cif_fecha_corte ON public.corrida_indexacion_financiera (fecha_corte);
CREATE INDEX IF NOT EXISTS idx_cif_hash_corrida ON public.corrida_indexacion_financiera (hash_corrida);
CREATE INDEX IF NOT EXISTS idx_cif_corrida_anterior ON public.corrida_indexacion_financiera (id_corrida_anterior);
CREATE INDEX IF NOT EXISTS idx_cif_corrida_reemplazante ON public.corrida_indexacion_financiera (id_corrida_reemplazante);
CREATE INDEX IF NOT EXISTS idx_cif_pendientes ON public.corrida_indexacion_financiera (fecha_corte, id_plan_pago_venta_bloque) WHERE deleted_at IS NULL AND estado_corrida = 'PENDIENTE_APLICACION';
CREATE INDEX IF NOT EXISTS idx_cif_activas ON public.corrida_indexacion_financiera (id_plan_pago_venta, id_plan_pago_venta_bloque, estado_corrida) WHERE deleted_at IS NULL AND estado_corrida NOT IN ('ANULADA','REEMPLAZADA');

CREATE INDEX IF NOT EXISTS idx_cifd_version_registro ON public.corrida_indexacion_financiera_detalle (version_registro);
CREATE INDEX IF NOT EXISTS idx_cifd_timestamps ON public.corrida_indexacion_financiera_detalle (created_at, updated_at, deleted_at);
CREATE INDEX IF NOT EXISTS idx_cifd_op_ids ON public.corrida_indexacion_financiera_detalle (op_id_alta, op_id_ultima_modificacion);
CREATE INDEX IF NOT EXISTS idx_cifd_obligacion ON public.corrida_indexacion_financiera_detalle (id_obligacion_financiera);
CREATE INDEX IF NOT EXISTS idx_cifd_elegibilidad ON public.corrida_indexacion_financiera_detalle (estado_elegibilidad);
CREATE INDEX IF NOT EXISTS idx_cifd_codigo_error ON public.corrida_indexacion_financiera_detalle (codigo_error);

CREATE OR REPLACE FUNCTION public.trg_cifd_validar_composiciones() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    IF NEW.id_composicion_capital_venta IS NOT NULL AND NOT EXISTS (
        SELECT 1
          FROM public.composicion_obligacion co
          JOIN public.concepto_financiero cf
            ON cf.id_concepto_financiero = co.id_concepto_financiero
         WHERE co.id_composicion_obligacion = NEW.id_composicion_capital_venta
           AND co.id_obligacion_financiera = NEW.id_obligacion_financiera
           AND cf.codigo_concepto_financiero = 'CAPITAL_VENTA'
    ) THEN
        RAISE EXCEPTION 'corrida_indexacion_financiera_detalle: id_composicion_capital_venta debe pertenecer a la obligacion y usar concepto CAPITAL_VENTA';
    END IF;

    IF NEW.id_composicion_ajuste_indexacion IS NOT NULL AND NOT EXISTS (
        SELECT 1
          FROM public.composicion_obligacion co
          JOIN public.concepto_financiero cf
            ON cf.id_concepto_financiero = co.id_concepto_financiero
         WHERE co.id_composicion_obligacion = NEW.id_composicion_ajuste_indexacion
           AND co.id_obligacion_financiera = NEW.id_obligacion_financiera
           AND cf.codigo_concepto_financiero = 'AJUSTE_INDEXACION'
    ) THEN
        RAISE EXCEPTION 'corrida_indexacion_financiera_detalle: id_composicion_ajuste_indexacion debe pertenecer a la obligacion y usar concepto AJUSTE_INDEXACION';
    END IF;

    RETURN NEW;
END;
$$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trg_bi_cif_core_ef' AND tgrelid = 'public.corrida_indexacion_financiera'::regclass) THEN
        CREATE TRIGGER trg_bi_cif_core_ef BEFORE INSERT ON public.corrida_indexacion_financiera FOR EACH ROW EXECUTE FUNCTION public.trg_core_ef_sync_defaults_insert();
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trg_bu_cif_core_ef' AND tgrelid = 'public.corrida_indexacion_financiera'::regclass) THEN
        CREATE TRIGGER trg_bu_cif_core_ef BEFORE UPDATE ON public.corrida_indexacion_financiera FOR EACH ROW EXECUTE FUNCTION public.trg_core_ef_sync_defaults_update();
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trg_biu_cifd_validar_composiciones' AND tgrelid = 'public.corrida_indexacion_financiera_detalle'::regclass) THEN
        CREATE TRIGGER trg_biu_cifd_validar_composiciones BEFORE INSERT OR UPDATE ON public.corrida_indexacion_financiera_detalle FOR EACH ROW EXECUTE FUNCTION public.trg_cifd_validar_composiciones();
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trg_bi_cifd_core_ef' AND tgrelid = 'public.corrida_indexacion_financiera_detalle'::regclass) THEN
        CREATE TRIGGER trg_bi_cifd_core_ef BEFORE INSERT ON public.corrida_indexacion_financiera_detalle FOR EACH ROW EXECUTE FUNCTION public.trg_core_ef_sync_defaults_insert();
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trg_bu_cifd_core_ef' AND tgrelid = 'public.corrida_indexacion_financiera_detalle'::regclass) THEN
        CREATE TRIGGER trg_bu_cifd_core_ef BEFORE UPDATE ON public.corrida_indexacion_financiera_detalle FOR EACH ROW EXECUTE FUNCTION public.trg_core_ef_sync_defaults_update();
    END IF;
END $$;

COMMENT ON TABLE public.corrida_indexacion_financiera IS 'Cabecera auditable de corrida de indexacion financiera V2 sobre una combinacion plan_pago_venta + plan_pago_venta_bloque.';
COMMENT ON TABLE public.corrida_indexacion_financiera_detalle IS 'Detalle por obligacion analizada en una corrida de indexacion financiera V2; incluye elegibles y excluidas.';
COMMENT ON INDEX public.ux_cif_idempotencia_funcional_activa IS 'Clave idempotente activa: plan+bloque+indice+valor aplicado+fecha de corte+origen+hash, excluyendo anuladas/reemplazadas y soft-deleted.';
COMMENT ON FUNCTION public.trg_cifd_validar_composiciones() IS 'Validacion estructural: las composiciones opcionales del detalle deben pertenecer a la obligacion y usar CAPITAL_VENTA/AJUSTE_INDEXACION segun corresponda.';
