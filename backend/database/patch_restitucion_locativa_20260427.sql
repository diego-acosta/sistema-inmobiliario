-- patch_restitucion_locativa_20260427.sql
-- Implementa tabla restitucion_locativa (dominio locativo) con garantía de unicidad por contrato

CREATE SEQUENCE IF NOT EXISTS public.restitucion_locativa_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

CREATE TABLE IF NOT EXISTS public.restitucion_locativa (
    id_restitucion_locativa bigint NOT NULL DEFAULT nextval('public.restitucion_locativa_id_seq'::regclass),
    uid_global              uuid    NOT NULL DEFAULT gen_random_uuid(),
    version_registro        integer NOT NULL DEFAULT 1,
    created_at              timestamp without time zone NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at              timestamp without time zone NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at              timestamp without time zone,
    id_instalacion_origen               bigint,
    id_instalacion_ultima_modificacion  bigint,
    op_id_alta                          uuid,
    op_id_ultima_modificacion           uuid,
    id_contrato_alquiler    bigint NOT NULL,
    fecha_restitucion       date   NOT NULL,
    estado_inmueble         character varying(50),
    observaciones           text,
    CONSTRAINT restitucion_locativa_pkey PRIMARY KEY (id_restitucion_locativa),
    CONSTRAINT fk_restitucion_locativa_contrato
        FOREIGN KEY (id_contrato_alquiler)
        REFERENCES public.contrato_alquiler(id_contrato_alquiler)
        ON DELETE RESTRICT
);

ALTER SEQUENCE public.restitucion_locativa_id_seq
    OWNED BY public.restitucion_locativa.id_restitucion_locativa;

CREATE UNIQUE INDEX IF NOT EXISTS uq_restitucion_locativa_contrato
    ON public.restitucion_locativa (id_contrato_alquiler)
    WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_restitucion_locativa_uid_global
    ON public.restitucion_locativa (uid_global);
