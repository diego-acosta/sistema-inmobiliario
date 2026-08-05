-- #441: metadata default-deny de editabilidad administrativa en parametro_sistema.
-- No crea definiciones, valores, endpoints, outbox, historial, índices, triggers ni funciones.
BEGIN;

LOCK TABLE public.parametro_sistema IN ACCESS EXCLUSIVE MODE;

DO $$
DECLARE
    actual_type text;
    actual_not_null boolean;
    actual_default text;
BEGIN
    IF to_regclass('public.parametro_sistema') IS NULL THEN
        RAISE EXCEPTION 'falta tabla requerida parametro_sistema';
    END IF;

    SELECT
        format_type(a.atttypid, a.atttypmod),
        a.attnotnull,
        pg_get_expr(d.adbin, d.adrelid)
      INTO actual_type, actual_not_null, actual_default
      FROM pg_attribute a
      LEFT JOIN pg_attrdef d
        ON d.adrelid = a.attrelid AND d.adnum = a.attnum
     WHERE a.attrelid = 'public.parametro_sistema'::regclass
       AND a.attname = 'editable_administrativamente'
       AND NOT a.attisdropped;

    IF actual_type IS NOT NULL AND actual_type <> 'boolean' THEN
        RAISE EXCEPTION 'columna parametro_sistema.editable_administrativamente incompatible: tipo %', actual_type;
    END IF;
    IF actual_type IS NOT NULL AND NOT actual_not_null THEN
        RAISE EXCEPTION 'columna parametro_sistema.editable_administrativamente incompatible: debe ser NOT NULL';
    END IF;
    IF actual_type IS NOT NULL
       AND COALESCE(regexp_replace(actual_default, '[[:space:]()]|::boolean', '', 'g'), '') <> 'false' THEN
        RAISE EXCEPTION 'default de parametro_sistema.editable_administrativamente incompatible: %', actual_default;
    END IF;
    IF actual_type IS NOT NULL THEN
        EXECUTE 'SELECT EXISTS (SELECT 1 FROM public.parametro_sistema WHERE editable_administrativamente IS NULL)'
          INTO actual_not_null;
        IF actual_not_null THEN
            RAISE EXCEPTION 'filas con parametro_sistema.editable_administrativamente NULL';
        END IF;
    END IF;
END $$;

ALTER TABLE public.parametro_sistema
    ADD COLUMN IF NOT EXISTS editable_administrativamente boolean NOT NULL DEFAULT false;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM public.parametro_sistema WHERE editable_administrativamente IS NULL) THEN
        RAISE EXCEPTION 'filas con parametro_sistema.editable_administrativamente NULL';
    END IF;
END $$;

COMMIT;
