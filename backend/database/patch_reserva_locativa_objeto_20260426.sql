-- Patch estructural: materializacion multiobjeto de reserva_locativa
-- Fecha: 2026-04-26

CREATE SEQUENCE IF NOT EXISTS public.reserva_locativa_objeto_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

CREATE TABLE IF NOT EXISTS public.reserva_locativa_objeto (
    id_reserva_locativa_objeto bigint NOT NULL DEFAULT nextval('public.reserva_locativa_objeto_id_seq'::regclass),
    uid_global uuid DEFAULT gen_random_uuid() NOT NULL,
    version_registro integer DEFAULT 1 NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    deleted_at timestamp without time zone,
    id_instalacion_origen bigint,
    id_instalacion_ultima_modificacion bigint,
    op_id_alta uuid,
    op_id_ultima_modificacion uuid,
    id_reserva_locativa bigint NOT NULL,
    id_inmueble bigint,
    id_unidad_funcional bigint,
    observaciones text,
    CONSTRAINT chk_rlo_xor CHECK (
        ((id_inmueble IS NOT NULL) AND (id_unidad_funcional IS NULL))
        OR ((id_inmueble IS NULL) AND (id_unidad_funcional IS NOT NULL))
    )
);

ALTER SEQUENCE public.reserva_locativa_objeto_id_seq
    OWNED BY public.reserva_locativa_objeto.id_reserva_locativa_objeto;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'reserva_locativa_objeto_pkey'
    ) THEN
        ALTER TABLE ONLY public.reserva_locativa_objeto
            ADD CONSTRAINT reserva_locativa_objeto_pkey
            PRIMARY KEY (id_reserva_locativa_objeto);
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'uq_rlo_uid_global'
    ) THEN
        ALTER TABLE ONLY public.reserva_locativa_objeto
            ADD CONSTRAINT uq_rlo_uid_global UNIQUE (uid_global);
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'fk_rlo_reserva'
    ) THEN
        ALTER TABLE ONLY public.reserva_locativa_objeto
            ADD CONSTRAINT fk_rlo_reserva
            FOREIGN KEY (id_reserva_locativa)
            REFERENCES public.reserva_locativa(id_reserva_locativa) ON DELETE RESTRICT;
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'fk_rlo_inmueble'
    ) THEN
        ALTER TABLE ONLY public.reserva_locativa_objeto
            ADD CONSTRAINT fk_rlo_inmueble
            FOREIGN KEY (id_inmueble)
            REFERENCES public.inmueble(id_inmueble) ON DELETE RESTRICT;
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'fk_rlo_unidad'
    ) THEN
        ALTER TABLE ONLY public.reserva_locativa_objeto
            ADD CONSTRAINT fk_rlo_unidad
            FOREIGN KEY (id_unidad_funcional)
            REFERENCES public.unidad_funcional(id_unidad_funcional) ON DELETE RESTRICT;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_rlo_reserva
    ON public.reserva_locativa_objeto USING btree (id_reserva_locativa);

CREATE INDEX IF NOT EXISTS idx_rlo_inmueble
    ON public.reserva_locativa_objeto USING btree (id_inmueble);

CREATE INDEX IF NOT EXISTS idx_rlo_unidad
    ON public.reserva_locativa_objeto USING btree (id_unidad_funcional);

CREATE INDEX IF NOT EXISTS idx_rlo_uid_global
    ON public.reserva_locativa_objeto USING btree (uid_global);

-- Unicidad dentro de la misma reserva: evita duplicar el mismo objeto en una reserva
CREATE UNIQUE INDEX IF NOT EXISTS uq_rlo_reserva_inmueble
    ON public.reserva_locativa_objeto USING btree (id_reserva_locativa, id_inmueble)
    WHERE ((deleted_at IS NULL) AND (id_inmueble IS NOT NULL));

CREATE UNIQUE INDEX IF NOT EXISTS uq_rlo_reserva_unidad
    ON public.reserva_locativa_objeto USING btree (id_reserva_locativa, id_unidad_funcional)
    WHERE ((deleted_at IS NULL) AND (id_unidad_funcional IS NOT NULL));
