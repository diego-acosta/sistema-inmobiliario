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
    ADD COLUMN IF NOT EXISTS attempt_id uuid,
    ADD COLUMN IF NOT EXISTS worker_id varchar(100),
    ADD COLUMN IF NOT EXISTS lease_expires_at timestamp without time zone,
    ADD COLUMN IF NOT EXISTS fence_generation bigint NOT NULL DEFAULT 0;

CREATE TABLE IF NOT EXISTS public.inbox_operation_scope (
    consumer varchar(100) NOT NULL,
    op_id uuid NOT NULL,
    payload_fingerprint varchar(64) NOT NULL,
    attempt_id uuid,
    worker_id varchar(100),
    lease_expires_at timestamp without time zone,
    fence_generation bigint NOT NULL DEFAULT 0,
    terminal_status varchar(20),
    updated_at timestamp without time zone NOT NULL DEFAULT
        (clock_timestamp() AT TIME ZONE 'UTC'),
    CONSTRAINT pk_inbox_operation_scope_511 PRIMARY KEY (consumer, op_id),
    CONSTRAINT ck_inbox_operation_scope_lease_511 CHECK (
        (attempt_id IS NULL) = (lease_expires_at IS NULL)
        AND (attempt_id IS NOT NULL OR worker_id IS NULL)
    ),
    CONSTRAINT ck_inbox_operation_scope_generation_511 CHECK (fence_generation >= 0),
    CONSTRAINT ck_inbox_operation_scope_terminal_511 CHECK (
        terminal_status IS NULL OR terminal_status IN ('PROCESSED', 'CONFLICTO')
    ),
    CONSTRAINT ck_inbox_operation_scope_fingerprint_511 CHECK (
        payload_fingerprint ~ '^[0-9a-f]{64}$'
    )
);

CREATE TEMP TABLE inbox_operation_scope_contract_probe_511
    (LIKE public.inbox_operation_scope INCLUDING DEFAULTS)
    ON COMMIT DROP;
ALTER TABLE inbox_operation_scope_contract_probe_511
    ADD CONSTRAINT expected_terminal_511 CHECK (
        terminal_status IS NULL OR terminal_status IN ('PROCESSED', 'CONFLICTO')
    ),
    ADD CONSTRAINT legacy_terminal_511 CHECK (terminal_status IS NULL);

CREATE TEMP TABLE inbox_event_version_contract_probe_511
    (version_registro integer)
    ON COMMIT DROP;
ALTER TABLE inbox_event_version_contract_probe_511
    ADD CONSTRAINT expected_version_registro_511 CHECK (
        version_registro IS NULL OR version_registro >= 1
    );

CREATE TEMP TABLE inbox_event_envelope_contract_probe_511 (
    op_id uuid,
    aggregate_uid uuid,
    version_registro integer,
    payload jsonb,
    payload_fingerprint varchar(64),
    provenance jsonb
) ON COMMIT DROP;
ALTER TABLE inbox_event_envelope_contract_probe_511
    ADD CONSTRAINT expected_envelope_identity_511 CHECK (
        op_id IS NOT NULL
        OR (
            aggregate_uid IS NULL
            AND version_registro IS NULL
            AND payload IS NULL
            AND payload_fingerprint IS NULL
            AND provenance IS NULL
        )
    );

CREATE TEMP TABLE inbox_event_lifecycle_contract_probe_511
    (LIKE public.inbox_event)
    ON COMMIT DROP;
ALTER TABLE inbox_event_lifecycle_contract_probe_511
    ADD CONSTRAINT expected_pending_shape_511 CHECK (
        status <> 'PENDING_DEPENDENCY'
        OR (
            op_id IS NOT NULL
            AND aggregate_uid IS NOT NULL
            AND payload IS NOT NULL
            AND payload_fingerprint IS NOT NULL
            AND attempt_id IS NULL
            AND worker_id IS NULL
            AND lease_expires_at IS NULL
            AND processed_at IS NULL
        )
    ),
    ADD CONSTRAINT expected_processing_shape_511 CHECK (
        status <> 'PROCESSING'
        OR (
            op_id IS NULL
            AND aggregate_uid IS NULL
            AND version_registro IS NULL
            AND payload IS NULL
            AND payload_fingerprint IS NULL
            AND provenance IS NULL
            AND attempt_id IS NULL
            AND worker_id IS NULL
            AND lease_expires_at IS NULL
            AND processed_at IS NULL
        )
        OR (
            op_id IS NOT NULL
            AND aggregate_uid IS NOT NULL
            AND payload IS NOT NULL
            AND payload_fingerprint IS NOT NULL
            AND attempt_id IS NOT NULL
            AND lease_expires_at IS NOT NULL
            AND processed_at IS NULL
        )
    ),
    ADD CONSTRAINT expected_terminal_shape_511 CHECK (
        status NOT IN ('PROCESSED', 'REJECTED', 'CONFLICTO')
        OR (
            attempt_id IS NULL
            AND worker_id IS NULL
            AND lease_expires_at IS NULL
            AND next_attempt_at IS NULL
            AND processed_at IS NOT NULL
        )
    ),
    ADD CONSTRAINT expected_legacy_status_511 CHECK (
        op_id IS NOT NULL OR status IN ('PROCESSING', 'PROCESSED', 'REJECTED')
    ),
    ADD CONSTRAINT expected_portable_payload_511 CHECK (
        op_id IS NULL OR payload IS NOT NULL
    ),
    ADD CONSTRAINT expected_nonterminal_processed_511 CHECK (
        status NOT IN ('PENDING_DEPENDENCY', 'PROCESSING') OR processed_at IS NULL
    );

DO $scope_contract$
DECLARE
    actual text;
    expected_terminal text;
    legacy_terminal text;
    terminal_validated boolean;
BEGIN
    IF (SELECT count(*) FROM information_schema.columns
        WHERE table_schema='public' AND table_name='inbox_operation_scope'
          AND (column_name, data_type) IN (
            ('consumer', 'character varying'), ('op_id', 'uuid'),
            ('payload_fingerprint', 'character varying'),
            ('attempt_id', 'uuid'), ('worker_id', 'character varying'),
            ('lease_expires_at', 'timestamp without time zone'),
            ('fence_generation', 'bigint'), ('terminal_status', 'character varying'),
            ('updated_at', 'timestamp without time zone')
          )) <> 9 THEN
        RAISE EXCEPTION 'inbox_operation_scope has an incompatible definition';
    END IF;
    SELECT pg_get_constraintdef(oid) INTO actual FROM pg_constraint
     WHERE conrelid='public.inbox_operation_scope'::regclass
       AND conname='pk_inbox_operation_scope_511';
    IF actual IS NULL OR actual !~ 'PRIMARY KEY.*consumer, op_id' THEN
        RAISE EXCEPTION 'pk_inbox_operation_scope_511 has an incompatible definition';
    END IF;
    SELECT pg_get_expr(conbin, conrelid, false), convalidated
      INTO actual, terminal_validated
      FROM pg_constraint
     WHERE conrelid='public.inbox_operation_scope'::regclass
       AND conname='ck_inbox_operation_scope_terminal_511';
    SELECT pg_get_expr(conbin, conrelid, false) INTO expected_terminal
      FROM pg_constraint
     WHERE conrelid='inbox_operation_scope_contract_probe_511'::regclass
       AND conname='expected_terminal_511';
    SELECT pg_get_expr(conbin, conrelid, false) INTO legacy_terminal
      FROM pg_constraint
     WHERE conrelid='inbox_operation_scope_contract_probe_511'::regclass
       AND conname='legacy_terminal_511';
    IF actual = legacy_terminal AND terminal_validated THEN
        IF EXISTS (
            SELECT 1 FROM public.inbox_operation_scope
             WHERE terminal_status IS NOT NULL
               AND terminal_status NOT IN ('PROCESSED', 'CONFLICTO')
        ) THEN
            RAISE EXCEPTION 'legacy inbox_operation_scope terminal data is not migrable';
        END IF;
        ALTER TABLE public.inbox_operation_scope
            DROP CONSTRAINT ck_inbox_operation_scope_terminal_511;
        ALTER TABLE public.inbox_operation_scope
            ADD CONSTRAINT ck_inbox_operation_scope_terminal_511 CHECK (
                terminal_status IS NULL
                OR terminal_status IN ('PROCESSED', 'CONFLICTO')
            );
        SELECT pg_get_expr(conbin, conrelid, false), convalidated
          INTO actual, terminal_validated
          FROM pg_constraint
         WHERE conrelid='public.inbox_operation_scope'::regclass
           AND conname='ck_inbox_operation_scope_terminal_511';
    END IF;
    IF actual IS DISTINCT FROM expected_terminal OR NOT terminal_validated THEN
        RAISE EXCEPTION 'ck_inbox_operation_scope_terminal_511 has an incompatible definition';
    END IF;
END
$scope_contract$;

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
        ('attempt_id', 'uuid', false, NULL::text),
        ('worker_id', 'character varying(100)', false, NULL::text),
        ('lease_expires_at', 'timestamp without time zone', false, NULL::text),
        ('fence_generation', 'bigint', true, '0'::text)
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
    IF NOT EXISTS (SELECT 1 FROM pg_constraint
                   WHERE conrelid = 'public.inbox_event'::regclass
                     AND conname = 'ck_inbox_event_version_registro_511') THEN
        IF EXISTS (
            SELECT 1 FROM public.inbox_event
             WHERE version_registro IS NOT NULL AND version_registro < 1
        ) THEN
            RAISE EXCEPTION 'inbox_event has non-positive version_registro data';
        END IF;
        ALTER TABLE public.inbox_event
            ADD CONSTRAINT ck_inbox_event_version_registro_511
            CHECK (version_registro IS NULL OR version_registro >= 1);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint
                   WHERE conrelid = 'public.inbox_event'::regclass
                     AND conname = 'ck_inbox_event_envelope_identity_511') THEN
        IF EXISTS (
            SELECT 1 FROM public.inbox_event
             WHERE op_id IS NULL
               AND (
                   aggregate_uid IS NOT NULL
                   OR version_registro IS NOT NULL
                   OR payload IS NOT NULL
                   OR payload_fingerprint IS NOT NULL
                   OR provenance IS NOT NULL
               )
        ) THEN
            RAISE EXCEPTION 'inbox_event has a partial retained envelope without op_id';
        END IF;
        ALTER TABLE public.inbox_event
            ADD CONSTRAINT ck_inbox_event_envelope_identity_511 CHECK (
                op_id IS NOT NULL
                OR (
                    aggregate_uid IS NULL
                    AND version_registro IS NULL
                    AND payload IS NULL
                    AND payload_fingerprint IS NULL
                    AND provenance IS NULL
                )
            );
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_inbox_event_fingerprint_511') THEN
        ALTER TABLE public.inbox_event ADD CONSTRAINT ck_inbox_event_fingerprint_511
            CHECK (payload_fingerprint IS NULL OR payload_fingerprint ~ '^[0-9a-f]{64}$');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_inbox_event_lease_511') THEN
        ALTER TABLE public.inbox_event ADD CONSTRAINT ck_inbox_event_lease_511
            CHECK ((attempt_id IS NULL) = (lease_expires_at IS NULL)
                   AND (attempt_id IS NOT NULL OR worker_id IS NULL));
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_inbox_event_fence_generation_511') THEN
        ALTER TABLE public.inbox_event ADD CONSTRAINT ck_inbox_event_fence_generation_511
            CHECK (fence_generation >= 0);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint
                   WHERE conrelid = 'public.inbox_event'::regclass
                     AND conname = 'ck_inbox_event_portable_target_511') THEN
        ALTER TABLE public.inbox_event ADD CONSTRAINT ck_inbox_event_portable_target_511
            CHECK (op_id IS NULL OR aggregate_uid IS NOT NULL);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint
                   WHERE conrelid = 'public.inbox_event'::regclass
                     AND conname = 'ck_inbox_event_scoped_fingerprint_511') THEN
        ALTER TABLE public.inbox_event
            ADD CONSTRAINT ck_inbox_event_scoped_fingerprint_511
            CHECK (op_id IS NULL OR payload_fingerprint IS NOT NULL);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint
                   WHERE conrelid = 'public.inbox_event'::regclass
                     AND conname = 'ck_inbox_event_pending_shape_511') THEN
        IF EXISTS (
            SELECT 1 FROM public.inbox_event
             WHERE status = 'PENDING_DEPENDENCY'
               AND NOT (
                   op_id IS NOT NULL
                   AND aggregate_uid IS NOT NULL
                   AND payload IS NOT NULL
                   AND payload_fingerprint IS NOT NULL
                   AND attempt_id IS NULL
                   AND worker_id IS NULL
                   AND lease_expires_at IS NULL
                   AND processed_at IS NULL
               )
        ) THEN
            RAISE EXCEPTION 'inbox_event has an invalid PENDING_DEPENDENCY shape';
        END IF;
        ALTER TABLE public.inbox_event
            ADD CONSTRAINT ck_inbox_event_pending_shape_511 CHECK (
                status <> 'PENDING_DEPENDENCY'
                OR (
                    op_id IS NOT NULL
                    AND aggregate_uid IS NOT NULL
                    AND payload IS NOT NULL
                    AND payload_fingerprint IS NOT NULL
                    AND attempt_id IS NULL
                    AND worker_id IS NULL
                    AND lease_expires_at IS NULL
                    AND processed_at IS NULL
                )
            );
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint
                   WHERE conrelid = 'public.inbox_event'::regclass
                     AND conname = 'ck_inbox_event_processing_shape_511') THEN
        IF EXISTS (
            SELECT 1 FROM public.inbox_event
             WHERE status = 'PROCESSING'
               AND NOT (
                   (
                       op_id IS NULL
                       AND aggregate_uid IS NULL
                       AND version_registro IS NULL
                       AND payload IS NULL
                       AND payload_fingerprint IS NULL
                       AND provenance IS NULL
                       AND attempt_id IS NULL
                       AND worker_id IS NULL
                       AND lease_expires_at IS NULL
                       AND processed_at IS NULL
                   )
                   OR (
                       op_id IS NOT NULL
                       AND aggregate_uid IS NOT NULL
                       AND payload IS NOT NULL
                       AND payload_fingerprint IS NOT NULL
                       AND attempt_id IS NOT NULL
                       AND lease_expires_at IS NOT NULL
                       AND processed_at IS NULL
                   )
               )
        ) THEN
            RAISE EXCEPTION 'inbox_event has an invalid PROCESSING shape';
        END IF;
        ALTER TABLE public.inbox_event
            ADD CONSTRAINT ck_inbox_event_processing_shape_511 CHECK (
                status <> 'PROCESSING'
                OR (
                    op_id IS NULL
                    AND aggregate_uid IS NULL
                    AND version_registro IS NULL
                    AND payload IS NULL
                    AND payload_fingerprint IS NULL
                    AND provenance IS NULL
                    AND attempt_id IS NULL
                    AND worker_id IS NULL
                    AND lease_expires_at IS NULL
                    AND processed_at IS NULL
                )
                OR (
                    op_id IS NOT NULL
                    AND aggregate_uid IS NOT NULL
                    AND payload IS NOT NULL
                    AND payload_fingerprint IS NOT NULL
                    AND attempt_id IS NOT NULL
                    AND lease_expires_at IS NOT NULL
                    AND processed_at IS NULL
                )
            );
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint
                   WHERE conrelid = 'public.inbox_event'::regclass
                     AND conname = 'ck_inbox_event_terminal_shape_511') THEN
        IF EXISTS (
            SELECT 1 FROM public.inbox_event
             WHERE status IN ('PROCESSED', 'REJECTED', 'CONFLICTO')
               AND NOT (
                   attempt_id IS NULL
                   AND worker_id IS NULL
                   AND lease_expires_at IS NULL
                   AND next_attempt_at IS NULL
                   AND processed_at IS NOT NULL
               )
        ) THEN
            RAISE EXCEPTION 'inbox_event has an invalid terminal shape';
        END IF;
        ALTER TABLE public.inbox_event
            ADD CONSTRAINT ck_inbox_event_terminal_shape_511 CHECK (
                status NOT IN ('PROCESSED', 'REJECTED', 'CONFLICTO')
                OR (
                    attempt_id IS NULL
                    AND worker_id IS NULL
                    AND lease_expires_at IS NULL
                    AND next_attempt_at IS NULL
                    AND processed_at IS NOT NULL
                )
            );
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint
                   WHERE conrelid = 'public.inbox_event'::regclass
                     AND conname = 'ck_inbox_event_legacy_status_511') THEN
        IF EXISTS (
            SELECT 1 FROM public.inbox_event
             WHERE op_id IS NULL
               AND status NOT IN ('PROCESSING', 'PROCESSED', 'REJECTED')
        ) THEN
            RAISE EXCEPTION 'inbox_event has an invalid legacy status';
        END IF;
        ALTER TABLE public.inbox_event
            ADD CONSTRAINT ck_inbox_event_legacy_status_511 CHECK (
                op_id IS NOT NULL
                OR status IN ('PROCESSING', 'PROCESSED', 'REJECTED')
            );
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint
                   WHERE conrelid = 'public.inbox_event'::regclass
                     AND conname = 'ck_inbox_event_portable_payload_511') THEN
        IF EXISTS (
            SELECT 1 FROM public.inbox_event
             WHERE op_id IS NOT NULL AND payload IS NULL
        ) THEN
            RAISE EXCEPTION 'inbox_event has a portable envelope without payload';
        END IF;
        ALTER TABLE public.inbox_event
            ADD CONSTRAINT ck_inbox_event_portable_payload_511 CHECK (
                op_id IS NULL OR payload IS NOT NULL
            );
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_constraint
                   WHERE conrelid = 'public.inbox_event'::regclass
                     AND conname = 'ck_inbox_event_nonterminal_processed_511') THEN
        IF EXISTS (
            SELECT 1 FROM public.inbox_event
             WHERE status IN ('PENDING_DEPENDENCY', 'PROCESSING')
               AND processed_at IS NOT NULL
        ) THEN
            RAISE EXCEPTION 'inbox_event has processed_at in a non-terminal state';
        END IF;
        ALTER TABLE public.inbox_event
            ADD CONSTRAINT ck_inbox_event_nonterminal_processed_511 CHECK (
                status NOT IN ('PENDING_DEPENDENCY', 'PROCESSING')
                OR processed_at IS NULL
            );
    END IF;
END
$constraints$;

DO $constraint_contract$
DECLARE
    actual text;
    expected text;
    validated boolean;
    constraint_name text;
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
    SELECT pg_get_expr(conbin, conrelid, false), convalidated
      INTO actual, validated
      FROM pg_constraint
     WHERE conrelid='public.inbox_event'::regclass
       AND conname='ck_inbox_event_version_registro_511';
    SELECT pg_get_expr(conbin, conrelid, false) INTO expected
      FROM pg_constraint
     WHERE conrelid='inbox_event_version_contract_probe_511'::regclass
       AND conname='expected_version_registro_511';
    IF actual IS DISTINCT FROM expected OR NOT validated THEN
        RAISE EXCEPTION 'ck_inbox_event_version_registro_511 has an incompatible definition';
    END IF;
    SELECT pg_get_expr(conbin, conrelid, false), convalidated
      INTO actual, validated
      FROM pg_constraint
     WHERE conrelid='public.inbox_event'::regclass
       AND conname='ck_inbox_event_envelope_identity_511';
    SELECT pg_get_expr(conbin, conrelid, false) INTO expected
      FROM pg_constraint
     WHERE conrelid='inbox_event_envelope_contract_probe_511'::regclass
       AND conname='expected_envelope_identity_511';
    IF actual IS DISTINCT FROM expected OR NOT validated THEN
        RAISE EXCEPTION 'ck_inbox_event_envelope_identity_511 has an incompatible definition';
    END IF;
    SELECT pg_get_constraintdef(oid) INTO actual FROM pg_constraint
     WHERE conrelid='public.inbox_event'::regclass AND conname='ck_inbox_event_fingerprint_511';
    IF actual IS NULL OR actual !~ '\^\[0-9a-f\]\{64\}\$' THEN
        RAISE EXCEPTION 'ck_inbox_event_fingerprint_511 has an incompatible definition';
    END IF;
    SELECT pg_get_constraintdef(oid) INTO actual FROM pg_constraint
     WHERE conrelid='public.inbox_event'::regclass AND conname='ck_inbox_event_lease_511';
    IF actual IS NULL OR actual !~ 'attempt_id IS NULL.*lease_expires_at IS NULL' THEN
        RAISE EXCEPTION 'ck_inbox_event_lease_511 has an incompatible definition';
    END IF;
    SELECT pg_get_constraintdef(oid) INTO actual FROM pg_constraint
     WHERE conrelid='public.inbox_event'::regclass AND conname='ck_inbox_event_fence_generation_511';
    IF actual IS NULL OR replace(actual, ' ', '') <> 'CHECK((fence_generation>=0))' THEN
        RAISE EXCEPTION 'ck_inbox_event_fence_generation_511 has an incompatible definition';
    END IF;
    SELECT pg_get_constraintdef(oid) INTO actual FROM pg_constraint
     WHERE conrelid='public.inbox_event'::regclass
       AND conname='ck_inbox_event_portable_target_511';
    IF actual IS NULL OR actual !~ 'op_id IS NULL.*aggregate_uid IS NOT NULL' THEN
        RAISE EXCEPTION 'ck_inbox_event_portable_target_511 has an incompatible definition';
    END IF;
    SELECT pg_get_constraintdef(oid) INTO actual FROM pg_constraint
     WHERE conrelid='public.inbox_event'::regclass
       AND conname='ck_inbox_event_scoped_fingerprint_511';
    IF actual IS NULL OR actual !~ 'op_id IS NULL.*payload_fingerprint IS NOT NULL' THEN
        RAISE EXCEPTION 'ck_inbox_event_scoped_fingerprint_511 has an incompatible definition';
    END IF;
    FOR actual, expected, validated, constraint_name IN
        SELECT a.expression, e.expression, a.validated, names.actual_name
          FROM (VALUES
              ('ck_inbox_event_pending_shape_511', 'expected_pending_shape_511'),
              ('ck_inbox_event_processing_shape_511', 'expected_processing_shape_511'),
              ('ck_inbox_event_terminal_shape_511', 'expected_terminal_shape_511'),
              ('ck_inbox_event_legacy_status_511', 'expected_legacy_status_511'),
              ('ck_inbox_event_portable_payload_511', 'expected_portable_payload_511'),
              ('ck_inbox_event_nonterminal_processed_511', 'expected_nonterminal_processed_511')
          ) AS names(actual_name, expected_name)
          CROSS JOIN LATERAL (
              SELECT pg_get_expr(conbin, conrelid, false) AS expression,
                     convalidated AS validated
                FROM pg_constraint
               WHERE conrelid='public.inbox_event'::regclass
                 AND conname=names.actual_name
          ) a
          CROSS JOIN LATERAL (
              SELECT pg_get_expr(conbin, conrelid, false) AS expression
                FROM pg_constraint
               WHERE conrelid='inbox_event_lifecycle_contract_probe_511'::regclass
                 AND conname=names.expected_name
          ) e
    LOOP
        IF actual IS DISTINCT FROM expected OR NOT validated THEN
            RAISE EXCEPTION '% has an incompatible definition or is not validated',
                constraint_name;
        END IF;
    END LOOP;
    IF (SELECT count(*) FROM pg_constraint
         WHERE conrelid='public.inbox_event'::regclass
           AND conname IN (
               'ck_inbox_event_pending_shape_511',
               'ck_inbox_event_processing_shape_511',
               'ck_inbox_event_terminal_shape_511',
               'ck_inbox_event_legacy_status_511',
               'ck_inbox_event_portable_payload_511',
               'ck_inbox_event_nonterminal_processed_511'
           )) <> 6 THEN
        RAISE EXCEPTION 'inbox_event lifecycle constraints are incomplete';
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
