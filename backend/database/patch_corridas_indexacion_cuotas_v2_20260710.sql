-- Patch idempotente: trazabilidad fisica de corridas de indexacion financiera V2.
-- Alcance: tablas de cabecera y detalle para auditoria SQL de corridas de indexacion
-- de cuotas. No implementa endpoints, calculo financiero, caja, recibos ni documental.

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
    id_plan_pago_venta BIGINT NULL,
    id_plan_pago_venta_bloque BIGINT NULL,
    id_plan_pago_venta_bloque_indexacion BIGINT NULL,
    id_generacion_cronograma_financiero BIGINT NULL,
    id_indice_financiero BIGINT NULL,
    id_indice_financiero_valor_base BIGINT NULL,
    id_indice_financiero_valor_aplicado BIGINT NULL,
    fecha_base DATE NULL,
    fecha_corte DATE NOT NULL,
    fecha_calculo TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_publicacion_indice DATE NULL,
    valor_base_indice NUMERIC(18,8) NULL,
    valor_aplicado_indice NUMERIC(18,8) NULL,
    origen_corrida VARCHAR(60) NOT NULL,
    datos_origen JSONB NULL,
    referencia_funcional VARCHAR(180) NULL,
    estado_corrida VARCHAR(40) NOT NULL,
    hash_corrida VARCHAR(128) NULL,
    op_id UUID NULL,
    payload_hash VARCHAR(128) NULL,
    versiones_incluidas JSONB NULL,
    id_usuario BIGINT NULL,
    id_sucursal BIGINT NULL,
    id_instalacion_ejecucion BIGINT NULL,
    total_analizadas INTEGER NOT NULL DEFAULT 0,
    total_elegibles INTEGER NOT NULL DEFAULT 0,
    total_excluidas INTEGER NOT NULL DEFAULT 0,
    total_aplicadas INTEGER NOT NULL DEFAULT 0,
    importe_anterior_total NUMERIC(18,2) NULL,
    importe_nuevo_total NUMERIC(18,2) NULL,
    ajuste_total_anterior NUMERIC(18,2) NULL,
    ajuste_total_nuevo NUMERIC(18,2) NULL,
    saldo_anterior_total NUMERIC(18,2) NULL,
    saldo_nuevo_total NUMERIC(18,2) NULL,
    id_corrida_anterior BIGINT NULL,
    id_corrida_reemplazante BIGINT NULL,
    motivo TEXT NULL,
    outbox_estado VARCHAR(40) NULL,
    outbox_referencia VARCHAR(120) NULL,
    diagnostico_error TEXT NULL
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
    version_esperada INTEGER NULL,
    version_resultante INTEGER NULL,
    capital_base NUMERIC(18,2) NULL,
    id_composicion_capital_venta BIGINT NULL,
    id_indice_financiero_valor_base BIGINT NULL,
    id_indice_financiero_valor_aplicado BIGINT NULL,
    fecha_base_indice DATE NULL,
    fecha_aplicacion_indice DATE NULL,
    valor_base_indice NUMERIC(18,8) NULL,
    valor_aplicado_indice NUMERIC(18,8) NULL,
    coeficiente_indexacion NUMERIC(18,8) NULL,
    ajuste_anterior NUMERIC(18,2) NULL,
    ajuste_nuevo NUMERIC(18,2) NULL,
    diferencia_ajuste NUMERIC(18,2) NULL,
    importe_anterior NUMERIC(18,2) NULL,
    importe_nuevo NUMERIC(18,2) NULL,
    saldo_anterior NUMERIC(18,2) NULL,
    saldo_nuevo NUMERIC(18,2) NULL,
    elegibilidad VARCHAR(40) NOT NULL,
    motivo_exclusion TEXT NULL,
    error_tecnico TEXT NULL,
    snapshot_obligacion_antes JSONB NULL,
    snapshot_obligacion_despues JSONB NULL,
    snapshot_composiciones JSONB NULL,
    id_obligacion_financiera_indexacion BIGINT NULL
);

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_cif_uid_global' AND conrelid = 'public.corrida_indexacion_financiera'::regclass) THEN
        ALTER TABLE public.corrida_indexacion_financiera ADD CONSTRAINT uq_cif_uid_global UNIQUE (uid_global);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_cif_estado' AND conrelid = 'public.corrida_indexacion_financiera'::regclass) THEN
        ALTER TABLE public.corrida_indexacion_financiera ADD CONSTRAINT chk_cif_estado CHECK (estado_corrida IN ('BORRADOR', 'PREVISUALIZADA', 'PENDIENTE_APLICACION', 'APLICADA', 'FALLIDA', 'ANULADA', 'REEMPLAZADA'));
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_cif_origen' AND conrelid = 'public.corrida_indexacion_financiera'::regclass) THEN
        ALTER TABLE public.corrida_indexacion_financiera ADD CONSTRAINT chk_cif_origen CHECK (origen_corrida IN ('IMPORTACION_VENTA_HISTORICA', 'ALTA_MANUAL_VENTA_HISTORICA', 'PUBLICACION_INDICE', 'REINDEXACION_MANUAL', 'CORRECCION_INDICE', 'REPROCESO_CONTROLADO'));
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_cif_totales_no_negativos' AND conrelid = 'public.corrida_indexacion_financiera'::regclass) THEN
        ALTER TABLE public.corrida_indexacion_financiera ADD CONSTRAINT chk_cif_totales_no_negativos CHECK (total_analizadas >= 0 AND total_elegibles >= 0 AND total_excluidas >= 0 AND total_aplicadas >= 0);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_cif_plan_pago_venta' AND conrelid = 'public.corrida_indexacion_financiera'::regclass) THEN
        ALTER TABLE public.corrida_indexacion_financiera ADD CONSTRAINT fk_cif_plan_pago_venta FOREIGN KEY (id_plan_pago_venta) REFERENCES public.plan_pago_venta(id_plan_pago_venta) ON DELETE RESTRICT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_cif_plan_pago_venta_bloque' AND conrelid = 'public.corrida_indexacion_financiera'::regclass) THEN
        ALTER TABLE public.corrida_indexacion_financiera ADD CONSTRAINT fk_cif_plan_pago_venta_bloque FOREIGN KEY (id_plan_pago_venta_bloque) REFERENCES public.plan_pago_venta_bloque(id_plan_pago_venta_bloque) ON DELETE RESTRICT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_cif_plan_pago_venta_bloque_indexacion' AND conrelid = 'public.corrida_indexacion_financiera'::regclass) THEN
        ALTER TABLE public.corrida_indexacion_financiera ADD CONSTRAINT fk_cif_plan_pago_venta_bloque_indexacion FOREIGN KEY (id_plan_pago_venta_bloque_indexacion) REFERENCES public.plan_pago_venta_bloque_indexacion(id_plan_pago_venta_bloque_indexacion) ON DELETE RESTRICT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_cif_indice_financiero' AND conrelid = 'public.corrida_indexacion_financiera'::regclass) THEN
        ALTER TABLE public.corrida_indexacion_financiera ADD CONSTRAINT fk_cif_indice_financiero FOREIGN KEY (id_indice_financiero) REFERENCES public.indice_financiero(id_indice_financiero) ON DELETE RESTRICT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_cif_indice_valor_base' AND conrelid = 'public.corrida_indexacion_financiera'::regclass) THEN
        ALTER TABLE public.corrida_indexacion_financiera ADD CONSTRAINT fk_cif_indice_valor_base FOREIGN KEY (id_indice_financiero_valor_base) REFERENCES public.indice_financiero_valor(id_indice_financiero_valor) ON DELETE RESTRICT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_cif_indice_valor_aplicado' AND conrelid = 'public.corrida_indexacion_financiera'::regclass) THEN
        ALTER TABLE public.corrida_indexacion_financiera ADD CONSTRAINT fk_cif_indice_valor_aplicado FOREIGN KEY (id_indice_financiero_valor_aplicado) REFERENCES public.indice_financiero_valor(id_indice_financiero_valor) ON DELETE RESTRICT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_cif_corrida_anterior' AND conrelid = 'public.corrida_indexacion_financiera'::regclass) THEN
        ALTER TABLE public.corrida_indexacion_financiera ADD CONSTRAINT fk_cif_corrida_anterior FOREIGN KEY (id_corrida_anterior) REFERENCES public.corrida_indexacion_financiera(id_corrida_indexacion_financiera) ON DELETE RESTRICT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_cif_corrida_reemplazante' AND conrelid = 'public.corrida_indexacion_financiera'::regclass) THEN
        ALTER TABLE public.corrida_indexacion_financiera ADD CONSTRAINT fk_cif_corrida_reemplazante FOREIGN KEY (id_corrida_reemplazante) REFERENCES public.corrida_indexacion_financiera(id_corrida_indexacion_financiera) ON DELETE RESTRICT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_cifd_uid_global' AND conrelid = 'public.corrida_indexacion_financiera_detalle'::regclass) THEN
        ALTER TABLE public.corrida_indexacion_financiera_detalle ADD CONSTRAINT uq_cifd_uid_global UNIQUE (uid_global);
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_cifd_elegibilidad' AND conrelid = 'public.corrida_indexacion_financiera_detalle'::regclass) THEN
        ALTER TABLE public.corrida_indexacion_financiera_detalle ADD CONSTRAINT chk_cifd_elegibilidad CHECK (elegibilidad IN ('ELEGIBLE', 'EXCLUIDA', 'BLOQUEANTE', 'RESERVADA_FUTURA'));
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_cifd_corrida' AND conrelid = 'public.corrida_indexacion_financiera_detalle'::regclass) THEN
        ALTER TABLE public.corrida_indexacion_financiera_detalle ADD CONSTRAINT fk_cifd_corrida FOREIGN KEY (id_corrida_indexacion_financiera) REFERENCES public.corrida_indexacion_financiera(id_corrida_indexacion_financiera) ON DELETE CASCADE;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_cifd_obligacion_financiera' AND conrelid = 'public.corrida_indexacion_financiera_detalle'::regclass) THEN
        ALTER TABLE public.corrida_indexacion_financiera_detalle ADD CONSTRAINT fk_cifd_obligacion_financiera FOREIGN KEY (id_obligacion_financiera) REFERENCES public.obligacion_financiera(id_obligacion_financiera) ON DELETE RESTRICT;
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'fk_cifd_obligacion_indexacion' AND conrelid = 'public.corrida_indexacion_financiera_detalle'::regclass) THEN
        ALTER TABLE public.corrida_indexacion_financiera_detalle ADD CONSTRAINT fk_cifd_obligacion_indexacion FOREIGN KEY (id_obligacion_financiera_indexacion) REFERENCES public.obligacion_financiera_indexacion(id_obligacion_financiera_indexacion) ON DELETE RESTRICT;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_cif_estado_corrida ON public.corrida_indexacion_financiera (estado_corrida) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_cif_plan_bloque ON public.corrida_indexacion_financiera (id_plan_pago_venta, id_plan_pago_venta_bloque) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_cif_op_id ON public.corrida_indexacion_financiera (op_id) WHERE op_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_cifd_corrida ON public.corrida_indexacion_financiera_detalle (id_corrida_indexacion_financiera);
CREATE INDEX IF NOT EXISTS idx_cifd_obligacion ON public.corrida_indexacion_financiera_detalle (id_obligacion_financiera);
