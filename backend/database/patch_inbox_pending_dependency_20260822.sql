-- #511: lifecycle transversal de dependencias temporales del inbox.
BEGIN;

DO $contract$
BEGIN
    IF to_regclass('public.inbox_event') IS NULL THEN
        RAISE EXCEPTION 'inbox_event must exist before applying #511';
    END IF;
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'inbox_event'
          AND column_name = 'status' AND data_type <> 'character varying'
    ) THEN
        RAISE EXCEPTION 'inbox_event.status has an incompatible type';
    END IF;
END
$contract$;

ALTER TABLE public.inbox_event
    ADD COLUMN IF NOT EXISTS op_id uuid,
    ADD COLUMN IF NOT EXISTS aggregate_uid uuid,
    ADD COLUMN IF NOT EXISTS version_registro integer,
    ADD COLUMN IF NOT EXISTS payload jsonb,
    ADD COLUMN IF NOT EXISTS payload_fingerprint varchar(64),
    ADD COLUMN IF NOT EXISTS provenance jsonb,
    ADD COLUMN IF NOT EXISTS attempt_count integer NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS last_attempt_at timestamp without time zone,
    ADD COLUMN IF NOT EXISTS next_attempt_at timestamp without time zone,
    ADD COLUMN IF NOT EXISTS lease_owner varchar(100),
    ADD COLUMN IF NOT EXISTS lease_expires_at timestamp without time zone,
    ADD COLUMN IF NOT EXISTS lease_generation bigint NOT NULL DEFAULT 0;

DO $columns$
DECLARE
    spec record;
    actual record;
BEGIN
    FOR spec IN SELECT * FROM (VALUES
        ('op_id', 'uuid', false, NULL::text),
        ('aggregate_uid', 'uuid', false, NULL::text),
        ('version_registro', 'integer', false, NULL::text),
        ('payload', 'jsonb', false, NULL::text),
        ('payload_fingerprint', 'character varying(64)', false, NULL::text),
        ('provenance', 'jsonb', false, NULL::text),
        ('attempt_count', 'integer', true, '0'::text),
        ('last_attempt_at', 'timestamp without time zone', false, NULL::text),
        ('next_attempt_at', 'timestamp without time zone', false, NULL::text),
        ('lease_owner', 'character varying(100)', false, NULL::text),
        ('lease_expires_at', 'timestamp without time zone', false, NULL::text),
        ('lease_generation', 'bigint', true, '0'::text)
    ) AS expected(name, sql_type, not_null, default_expr)
    LOOP
        SELECT format_type(a.atttypid, a.atttypmod) AS sql_type,
               a.attnotnull AS not_null,
               pg_get_expr(d.adbin, d.adrelid) AS default_expr
          INTO actual
          FROM pg_attribute a
          LEFT JOIN pg_attrdef d ON d.adrelid = a.attrelid AND d.adnum = a.attnum
         WHERE a.attrelid = 'public.inbox_event'::regclass
           AND a.attname = spec.name AND NOT a.attisdropped;
        IF NOT FOUND OR actual.sql_type <> spec.sql_type
           OR actual.not_null <> spec.not_null
           OR actual.default_expr IS DISTINCT FROM spec.default_expr THEN
            RAISE EXCEPTION 'inbox_event.% has incompatible type/nullability/default', spec.name;
        END IF;
    END LOOP;
END
$columns$;

DO $constraints$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_inbox_event_status_511') THEN
        ALTER TABLE public.inbox_event ADD CONSTRAINT ck_inbox_event_status_511
            CHECK (status IN ('PENDING_DEPENDENCY','PROCESSING','PROCESSED','REJECTED','CONFLICTO'));
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_inbox_event_attempt_count_511') THEN
        ALTER TABLE public.inbox_event ADD CONSTRAINT ck_inbox_event_attempt_count_511
            CHECK (attempt_count >= 0);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_inbox_event_fingerprint_511') THEN
        ALTER TABLE public.inbox_event ADD CONSTRAINT ck_inbox_event_fingerprint_511
            CHECK (payload_fingerprint IS NULL OR payload_fingerprint ~ '^[0-9a-f]{64}$');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_inbox_event_lease_511') THEN
        ALTER TABLE public.inbox_event ADD CONSTRAINT ck_inbox_event_lease_511
            CHECK ((lease_owner IS NULL) = (lease_expires_at IS NULL));
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_inbox_event_lease_generation_511') THEN
        ALTER TABLE public.inbox_event ADD CONSTRAINT ck_inbox_event_lease_generation_511
            CHECK (lease_generation >= 0);
    END IF;
END
$constraints$;

DO $constraint_contract$
DECLARE
    actual text;
BEGIN
    SELECT pg_get_constraintdef(oid) INTO actual FROM pg_constraint
     WHERE conrelid='public.inbox_event'::regclass AND conname='ck_inbox_event_status_511';
    IF actual IS NULL OR actual !~ 'PENDING_DEPENDENCY.*PROCESSING.*PROCESSED.*REJECTED.*CONFLICTO' THEN
        RAISE EXCEPTION 'ck_inbox_event_status_511 has an incompatible definition';
    END IF;
    SELECT pg_get_constraintdef(oid) INTO actual FROM pg_constraint
     WHERE conrelid='public.inbox_event'::regclass AND conname='ck_inbox_event_attempt_count_511';
    IF actual IS NULL OR replace(actual, ' ', '') <> 'CHECK((attempt_count>=0))' THEN
        RAISE EXCEPTION 'ck_inbox_event_attempt_count_511 has an incompatible definition';
    END IF;
    SELECT pg_get_constraintdef(oid) INTO actual FROM pg_constraint
     WHERE conrelid='public.inbox_event'::regclass AND conname='ck_inbox_event_fingerprint_511';
    IF actual IS NULL OR actual !~ '\^\[0-9a-f\]\{64\}\$' THEN
        RAISE EXCEPTION 'ck_inbox_event_fingerprint_511 has an incompatible definition';
    END IF;
    SELECT pg_get_constraintdef(oid) INTO actual FROM pg_constraint
     WHERE conrelid='public.inbox_event'::regclass AND conname='ck_inbox_event_lease_511';
    IF actual IS NULL OR actual !~ 'lease_owner IS NULL.*lease_expires_at IS NULL' THEN
        RAISE EXCEPTION 'ck_inbox_event_lease_511 has an incompatible definition';
    END IF;
    SELECT pg_get_constraintdef(oid) INTO actual FROM pg_constraint
     WHERE conrelid='public.inbox_event'::regclass AND conname='ck_inbox_event_lease_generation_511';
    IF actual IS NULL OR replace(actual, ' ', '') <> 'CHECK((lease_generation>=0))' THEN
        RAISE EXCEPTION 'ck_inbox_event_lease_generation_511 has an incompatible definition';
    END IF;
END
$constraint_contract$;

CREATE INDEX IF NOT EXISTS idx_inbox_event_pending_eligible_511
    ON public.inbox_event (next_attempt_at, created_at, id)
    WHERE status = 'PENDING_DEPENDENCY';
CREATE INDEX IF NOT EXISTS idx_inbox_event_processing_lease_511
    ON public.inbox_event (lease_expires_at, id)
    WHERE status = 'PROCESSING' AND lease_expires_at IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_inbox_event_consumer_op_511
    ON public.inbox_event (consumer, op_id)
    WHERE op_id IS NOT NULL;

DO $index_contract$
DECLARE
    actual text;
BEGIN
    SELECT lower(regexp_replace(pg_get_indexdef(indexrelid), '\s+', ' ', 'g')) INTO actual
      FROM pg_index WHERE indexrelid='public.idx_inbox_event_pending_eligible_511'::regclass;
    IF actual IS NULL OR actual NOT LIKE '%using btree (next_attempt_at, created_at, id) where ((status)::text = ''pending_dependency''::text)%' THEN
        RAISE EXCEPTION 'idx_inbox_event_pending_eligible_511 has an incompatible definition';
    END IF;
    SELECT lower(regexp_replace(pg_get_indexdef(indexrelid), '\s+', ' ', 'g')) INTO actual
      FROM pg_index WHERE indexrelid='public.idx_inbox_event_processing_lease_511'::regclass;
    IF actual IS NULL OR actual NOT LIKE '%using btree (lease_expires_at, id) where (((status)::text = ''processing''::text) and (lease_expires_at is not null))%' THEN
        RAISE EXCEPTION 'idx_inbox_event_processing_lease_511 has an incompatible definition';
    END IF;
    SELECT lower(regexp_replace(pg_get_indexdef(indexrelid), '\s+', ' ', 'g')) INTO actual
      FROM pg_index WHERE indexrelid='public.idx_inbox_event_consumer_op_511'::regclass;
    IF actual IS NULL OR actual NOT LIKE '%using btree (consumer, op_id) where (op_id is not null)%' THEN
        RAISE EXCEPTION 'idx_inbox_event_consumer_op_511 has an incompatible definition';
    END IF;
END
$index_contract$;

COMMIT;
