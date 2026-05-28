-- Patch idempotente: soporte fisico base de indices financieros

CREATE TABLE IF NOT EXISTS indice_financiero (
    id_indice_financiero BIGSERIAL PRIMARY KEY,
    uid_global UUID NOT NULL DEFAULT gen_random_uuid(),
    version_registro INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP NULL,
    id_instalacion_origen BIGINT NULL,
    id_instalacion_ultima_modificacion BIGINT NULL,
    op_id_alta UUID NULL,
    op_id_ultima_modificacion UUID NULL,
    codigo_indice_financiero VARCHAR(50) NOT NULL,
    nombre_indice_financiero VARCHAR(150) NOT NULL,
    descripcion TEXT NULL,
    tipo_indice VARCHAR(50) NOT NULL,
    unidad_medida VARCHAR(50) NOT NULL,
    frecuencia_publicacion VARCHAR(50) NOT NULL,
    fuente_indice VARCHAR(150) NULL,
    estado_indice_financiero VARCHAR(30) NOT NULL,
    observaciones TEXT NULL
);

CREATE TABLE IF NOT EXISTS indice_financiero_valor (
    id_indice_financiero_valor BIGSERIAL PRIMARY KEY,
    uid_global UUID NOT NULL DEFAULT gen_random_uuid(),
    version_registro INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP NULL,
    id_instalacion_origen BIGINT NULL,
    id_instalacion_ultima_modificacion BIGINT NULL,
    op_id_alta UUID NULL,
    op_id_ultima_modificacion UUID NULL,
    id_indice_financiero BIGINT NOT NULL,
    fecha_valor DATE NOT NULL,
    valor_indice NUMERIC(18,8) NOT NULL,
    fecha_publicacion DATE NULL,
    fuente_valor VARCHAR(150) NULL,
    estado_valor_indice VARCHAR(30) NOT NULL,
    observaciones TEXT NULL
);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'uq_indice_financiero_uid_global'
    ) THEN
        ALTER TABLE indice_financiero
            ADD CONSTRAINT uq_indice_financiero_uid_global UNIQUE (uid_global);
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'ck_indice_financiero_estado'
    ) THEN
        ALTER TABLE indice_financiero
            ADD CONSTRAINT ck_indice_financiero_estado
            CHECK (estado_indice_financiero IN ('BORRADOR', 'ACTIVO', 'INACTIVO', 'ANULADO'));
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'ck_indice_financiero_deleted_at'
    ) THEN
        ALTER TABLE indice_financiero
            ADD CONSTRAINT ck_indice_financiero_deleted_at
            CHECK (deleted_at IS NULL OR deleted_at >= created_at);
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'uq_indice_financiero_valor_uid_global'
    ) THEN
        ALTER TABLE indice_financiero_valor
            ADD CONSTRAINT uq_indice_financiero_valor_uid_global UNIQUE (uid_global);
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'fk_indice_financiero_valor_indice_financiero'
    ) THEN
        ALTER TABLE indice_financiero_valor
            ADD CONSTRAINT fk_indice_financiero_valor_indice_financiero
            FOREIGN KEY (id_indice_financiero)
            REFERENCES indice_financiero (id_indice_financiero)
            ON DELETE RESTRICT;
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'ck_indice_financiero_valor_estado'
    ) THEN
        ALTER TABLE indice_financiero_valor
            ADD CONSTRAINT ck_indice_financiero_valor_estado
            CHECK (estado_valor_indice IN ('BORRADOR', 'PUBLICADO', 'ANULADO'));
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'ck_indice_financiero_valor_valor_positivo'
    ) THEN
        ALTER TABLE indice_financiero_valor
            ADD CONSTRAINT ck_indice_financiero_valor_valor_positivo
            CHECK (valor_indice > 0);
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'ck_indice_financiero_valor_fecha_publicacion'
    ) THEN
        ALTER TABLE indice_financiero_valor
            ADD CONSTRAINT ck_indice_financiero_valor_fecha_publicacion
            CHECK (fecha_publicacion IS NULL OR fecha_publicacion >= fecha_valor);
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'ck_indice_financiero_valor_deleted_at'
    ) THEN
        ALTER TABLE indice_financiero_valor
            ADD CONSTRAINT ck_indice_financiero_valor_deleted_at
            CHECK (deleted_at IS NULL OR deleted_at >= created_at);
    END IF;
END
$$;

CREATE INDEX IF NOT EXISTS idx_indice_financiero_uid_global
    ON indice_financiero (uid_global);

CREATE UNIQUE INDEX IF NOT EXISTS idx_indice_financiero_codigo_activo
    ON indice_financiero (codigo_indice_financiero)
    WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_indice_financiero_estado_activo
    ON indice_financiero (estado_indice_financiero)
    WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_indice_financiero_valor_uid_global
    ON indice_financiero_valor (uid_global);

CREATE UNIQUE INDEX IF NOT EXISTS idx_indice_financiero_valor_indice_fecha_activo
    ON indice_financiero_valor (id_indice_financiero, fecha_valor)
    WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_indice_financiero_valor_fecha_activo
    ON indice_financiero_valor (fecha_valor)
    WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_indice_financiero_valor_estado_activo
    ON indice_financiero_valor (estado_valor_indice)
    WHERE deleted_at IS NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_trigger
        WHERE tgname = 'trg_bi_indice_financiero_core_ef'
          AND tgrelid = 'public.indice_financiero'::regclass
    ) THEN
        CREATE TRIGGER trg_bi_indice_financiero_core_ef
        BEFORE INSERT ON public.indice_financiero
        FOR EACH ROW EXECUTE FUNCTION public.trg_core_ef_sync_defaults_insert();
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_trigger
        WHERE tgname = 'trg_bu_indice_financiero_core_ef'
          AND tgrelid = 'public.indice_financiero'::regclass
    ) THEN
        CREATE TRIGGER trg_bu_indice_financiero_core_ef
        BEFORE UPDATE ON public.indice_financiero
        FOR EACH ROW EXECUTE FUNCTION public.trg_core_ef_sync_defaults_update();
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_trigger
        WHERE tgname = 'trg_bi_indice_financiero_valor_core_ef'
          AND tgrelid = 'public.indice_financiero_valor'::regclass
    ) THEN
        CREATE TRIGGER trg_bi_indice_financiero_valor_core_ef
        BEFORE INSERT ON public.indice_financiero_valor
        FOR EACH ROW EXECUTE FUNCTION public.trg_core_ef_sync_defaults_insert();
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_trigger
        WHERE tgname = 'trg_bu_indice_financiero_valor_core_ef'
          AND tgrelid = 'public.indice_financiero_valor'::regclass
    ) THEN
        CREATE TRIGGER trg_bu_indice_financiero_valor_core_ef
        BEFORE UPDATE ON public.indice_financiero_valor
        FOR EACH ROW EXECUTE FUNCTION public.trg_core_ef_sync_defaults_update();
    END IF;
END $$;

