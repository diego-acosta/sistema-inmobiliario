-- Patch estructural: materializacion multiobjeto de reserva_venta
-- Fecha: 2026-04-21

CREATE SEQUENCE IF NOT EXISTS public.reserva_venta_objeto_inmobiliario_id_reserva_venta_objeto_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

CREATE TABLE IF NOT EXISTS public.reserva_venta_objeto_inmobiliario (
    id_reserva_venta_objeto bigint NOT NULL DEFAULT nextval('public.reserva_venta_objeto_inmobiliario_id_reserva_venta_objeto_seq'::regclass),
    uid_global uuid DEFAULT gen_random_uuid() NOT NULL,
    version_registro integer DEFAULT 1 NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    deleted_at timestamp without time zone,
    id_instalacion_origen bigint,
    id_instalacion_ultima_modificacion bigint,
    op_id_alta uuid,
    op_id_ultima_modificacion uuid,
    id_reserva_venta bigint NOT NULL,
    id_inmueble bigint,
    id_unidad_funcional bigint,
    observaciones text,
    CONSTRAINT chk_rvo_xor CHECK (
        ((id_inmueble IS NOT NULL) AND (id_unidad_funcional IS NULL))
        OR ((id_inmueble IS NULL) AND (id_unidad_funcional IS NOT NULL))
    )
);

ALTER SEQUENCE public.reserva_venta_objeto_inmobiliario_id_reserva_venta_objeto_seq
    OWNED BY public.reserva_venta_objeto_inmobiliario.id_reserva_venta_objeto;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'reserva_venta_objeto_inmobiliario_pkey'
    ) THEN
        ALTER TABLE ONLY public.reserva_venta_objeto_inmobiliario
            ADD CONSTRAINT reserva_venta_objeto_inmobiliario_pkey
            PRIMARY KEY (id_reserva_venta_objeto);
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'uq_reserva_venta_objeto_uid_global'
    ) THEN
        ALTER TABLE ONLY public.reserva_venta_objeto_inmobiliario
            ADD CONSTRAINT uq_reserva_venta_objeto_uid_global UNIQUE (uid_global);
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'fk_rvo_inmueble'
    ) THEN
        ALTER TABLE ONLY public.reserva_venta_objeto_inmobiliario
            ADD CONSTRAINT fk_rvo_inmueble
            FOREIGN KEY (id_inmueble) REFERENCES public.inmueble(id_inmueble) ON DELETE RESTRICT;
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'fk_rvo_reserva'
    ) THEN
        ALTER TABLE ONLY public.reserva_venta_objeto_inmobiliario
            ADD CONSTRAINT fk_rvo_reserva
            FOREIGN KEY (id_reserva_venta) REFERENCES public.reserva_venta(id_reserva_venta) ON DELETE RESTRICT;
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'fk_rvo_unidad'
    ) THEN
        ALTER TABLE ONLY public.reserva_venta_objeto_inmobiliario
            ADD CONSTRAINT fk_rvo_unidad
            FOREIGN KEY (id_unidad_funcional) REFERENCES public.unidad_funcional(id_unidad_funcional) ON DELETE RESTRICT;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_reserva_venta_objeto_uid_global
    ON public.reserva_venta_objeto_inmobiliario USING btree (uid_global);

CREATE INDEX IF NOT EXISTS idx_rvo_inmueble
    ON public.reserva_venta_objeto_inmobiliario USING btree (id_inmueble);

CREATE INDEX IF NOT EXISTS idx_rvo_reserva
    ON public.reserva_venta_objeto_inmobiliario USING btree (id_reserva_venta);

CREATE INDEX IF NOT EXISTS idx_rvo_unidad
    ON public.reserva_venta_objeto_inmobiliario USING btree (id_unidad_funcional);

CREATE UNIQUE INDEX IF NOT EXISTS uq_rvo_reserva_inmueble_activo
    ON public.reserva_venta_objeto_inmobiliario USING btree (id_reserva_venta, id_inmueble)
    WHERE ((deleted_at IS NULL) AND (id_inmueble IS NOT NULL));

CREATE UNIQUE INDEX IF NOT EXISTS uq_rvo_reserva_unidad_activo
    ON public.reserva_venta_objeto_inmobiliario USING btree (id_reserva_venta, id_unidad_funcional)
    WHERE ((deleted_at IS NULL) AND (id_unidad_funcional IS NOT NULL));
