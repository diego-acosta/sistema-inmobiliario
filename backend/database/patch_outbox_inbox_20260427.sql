-- patch_outbox_inbox_20260427.sql
-- Refactor outbox a versión robusta + tabla inbox_event

-- ── outbox_event: nuevas columnas ────────────────────────────────────────────

ALTER TABLE public.outbox_event
    ADD COLUMN IF NOT EXISTS event_id    uuid    DEFAULT gen_random_uuid() NOT NULL,
    ADD COLUMN IF NOT EXISTS processed_at timestamp without time zone,
    ADD COLUMN IF NOT EXISTS retry_count integer DEFAULT 0 NOT NULL,
    ADD COLUMN IF NOT EXISTS last_error  text;

CREATE UNIQUE INDEX IF NOT EXISTS uq_outbox_event_id
    ON public.outbox_event (event_id);

-- ── inbox_event ───────────────────────────────────────────────────────────────

CREATE SEQUENCE IF NOT EXISTS public.inbox_event_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

CREATE TABLE IF NOT EXISTS public.inbox_event (
    id            bigint          NOT NULL DEFAULT nextval('public.inbox_event_id_seq'::regclass),
    event_id      uuid            NOT NULL,
    event_type    varchar(100)    NOT NULL,
    aggregate_type varchar(100)   NOT NULL,
    aggregate_id  bigint          NOT NULL,
    consumer      varchar(100)    NOT NULL,
    status        varchar(20)     NOT NULL DEFAULT 'PROCESSING',
    processed_at  timestamp without time zone,
    error_detail  text,
    created_at    timestamp without time zone NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT inbox_event_pkey PRIMARY KEY (id),
    CONSTRAINT uq_inbox_event_consumer UNIQUE (event_id, consumer)
);

ALTER SEQUENCE public.inbox_event_id_seq OWNED BY public.inbox_event.id;

CREATE INDEX IF NOT EXISTS idx_inbox_event_lookup
    ON public.inbox_event USING btree (consumer, status, created_at);
