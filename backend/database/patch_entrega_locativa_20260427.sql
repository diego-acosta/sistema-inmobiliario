-- patch_entrega_locativa_20260427.sql
-- Implementa tabla entrega_locativa con garantía de unicidad por contrato

CREATE SEQUENCE IF NOT EXISTS public.entrega_locativa_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

CREATE TABLE IF NOT EXISTS public.entrega_locativa (
    id_entrega_locativa bigint NOT NULL DEFAULT nextval('public.entrega_locativa_id_seq'::regclass),
    uid_global          uuid    NOT NULL DEFAULT gen_random_uuid(),
    version_registro    integer NOT NULL DEFAULT 1,
    created_at          timestamp without time zone NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at          timestamp without time zone NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at          timestamp without time zone,
    id_instalacion_origen               bigint,
    id_instalacion_ultima_modificacion  bigint,
    op_id_alta                          uuid,
    op_id_ultima_modificacion           uuid,
    id_contrato_alquiler bigint NOT NULL,
    fecha_entrega        date   NOT NULL,
    observaciones        text,
    CONSTRAINT entrega_locativa_pkey PRIMARY KEY (id_entrega_locativa)
);

ALTER SEQUENCE public.entrega_locativa_id_seq
    OWNED BY public.entrega_locativa.id_entrega_locativa;

CREATE UNIQUE INDEX IF NOT EXISTS uq_entrega_locativa_contrato
    ON public.entrega_locativa (id_contrato_alquiler)
    WHERE deleted_at IS NULL;
