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
    ADD COLUMN IF NOT EXISTS lease_expires_at timestamp without time zone;

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
END
$constraints$;

CREATE INDEX IF NOT EXISTS idx_inbox_event_pending_eligible_511
    ON public.inbox_event (next_attempt_at, created_at, id)
    WHERE status = 'PENDING_DEPENDENCY';
CREATE INDEX IF NOT EXISTS idx_inbox_event_processing_lease_511
    ON public.inbox_event (lease_expires_at, id)
    WHERE status = 'PROCESSING' AND lease_expires_at IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_inbox_event_consumer_op_511
    ON public.inbox_event (consumer, op_id)
    WHERE op_id IS NOT NULL;

COMMIT;
