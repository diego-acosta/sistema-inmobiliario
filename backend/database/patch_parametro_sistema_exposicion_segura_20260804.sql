-- #438: metadata mínima de exposición segura en parametro_sistema.
-- No crea definiciones, valores, endpoints, outbox ni historial runtime.
BEGIN;

LOCK TABLE public.parametro_sistema IN ACCESS EXCLUSIVE MODE;

DO $$
DECLARE
    col record;
    actual_type text;
    actual_default text;
    actual_not_null boolean;
    constraint_def text;
BEGIN
    IF to_regclass('public.parametro_sistema') IS NULL THEN
        RAISE EXCEPTION 'falta tabla requerida parametro_sistema';
    END IF;

    FOR col IN
        SELECT * FROM (VALUES
            ('exponible_api_administrativa', 'boolean', 'false'),
            ('es_sensible', 'boolean', 'true')
        ) AS x(name, data_type, expected_default)
    LOOP
        SELECT
            format_type(a.atttypid, a.atttypmod),
            a.attnotnull,
            pg_get_expr(d.adbin, d.adrelid)
          INTO actual_type, actual_not_null, actual_default
          FROM pg_attribute a
          LEFT JOIN pg_attrdef d
            ON d.adrelid = a.attrelid AND d.adnum = a.attnum
         WHERE a.attrelid = 'public.parametro_sistema'::regclass
           AND a.attname = col.name
           AND NOT a.attisdropped;

        IF actual_type IS NOT NULL AND actual_type <> col.data_type THEN
            RAISE EXCEPTION 'columna parametro_sistema.% incompatible: tipo %', col.name, actual_type;
        END IF;
        IF actual_type IS NOT NULL AND NOT actual_not_null THEN
            RAISE EXCEPTION 'columna parametro_sistema.% incompatible: debe ser NOT NULL', col.name;
        END IF;
        IF actual_type IS NOT NULL AND COALESCE(regexp_replace(actual_default, '[[:space:]()]|::boolean', '', 'g'), '') <> col.expected_default THEN
            RAISE EXCEPTION 'default de parametro_sistema.% incompatible: %', col.name, actual_default;
        END IF;
    END LOOP;

    SELECT pg_get_constraintdef(oid)
      INTO constraint_def
      FROM pg_constraint
     WHERE conrelid = 'public.parametro_sistema'::regclass
       AND conname = 'chk_parametro_sistema_exposicion_no_sensible';

    IF constraint_def IS NOT NULL
       AND regexp_replace(constraint_def, '[[:space:]()]', '', 'g') <> 'CHECKNOTexponible_api_administrativaANDes_sensible' THEN
        RAISE EXCEPTION 'constraint chk_parametro_sistema_exposicion_no_sensible incompatible: %', constraint_def;
    END IF;

    IF EXISTS (
        SELECT 1
          FROM pg_attribute
         WHERE attrelid = 'public.parametro_sistema'::regclass
           AND attname IN ('exponible_api_administrativa', 'es_sensible')
           AND NOT attisdropped
         GROUP BY attrelid
        HAVING count(*) = 2
    ) THEN
        EXECUTE 'SELECT EXISTS (SELECT 1 FROM public.parametro_sistema WHERE exponible_api_administrativa IS TRUE AND es_sensible IS TRUE)'
          INTO actual_not_null;
        IF actual_not_null THEN
            RAISE EXCEPTION 'estado contradictorio en parametro_sistema: sensible y exponible';
        END IF;
    END IF;
END $$;

ALTER TABLE public.parametro_sistema
    ADD COLUMN IF NOT EXISTS exponible_api_administrativa boolean NOT NULL DEFAULT false,
    ADD COLUMN IF NOT EXISTS es_sensible boolean NOT NULL DEFAULT true;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
          FROM public.parametro_sistema
         WHERE exponible_api_administrativa IS TRUE
           AND es_sensible IS TRUE
    ) THEN
        RAISE EXCEPTION 'estado contradictorio en parametro_sistema: sensible y exponible';
    END IF;
END $$;

DO $$
DECLARE
    actual text;
BEGIN
    SELECT pg_get_constraintdef(oid)
      INTO actual
      FROM pg_constraint
     WHERE conrelid = 'public.parametro_sistema'::regclass
       AND conname = 'chk_parametro_sistema_exposicion_no_sensible';

    IF actual IS NULL THEN
        ALTER TABLE public.parametro_sistema
            ADD CONSTRAINT chk_parametro_sistema_exposicion_no_sensible
            CHECK (NOT (exponible_api_administrativa AND es_sensible));
    ELSIF regexp_replace(actual, '[[:space:]()]', '', 'g') <> 'CHECKNOTexponible_api_administrativaANDes_sensible' THEN
        RAISE EXCEPTION 'constraint chk_parametro_sistema_exposicion_no_sensible incompatible: %', actual;
    END IF;
END $$;

COMMIT;
