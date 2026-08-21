-- #508 Administrativo: identidad portable canónica de usuario.
BEGIN;

LOCK TABLE public.usuario IN ACCESS EXCLUSIVE MODE;

ALTER TABLE public.usuario
    ADD COLUMN IF NOT EXISTS uid_global uuid;

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema = 'public'
          AND table_name = 'usuario'
          AND column_name = 'uid_global'
          AND data_type <> 'uuid'
    ) THEN
        RAISE EXCEPTION 'usuario.uid_global incompatible: debe ser uuid';
    END IF;
END $$;

-- Cada fila heredada recibe una identidad nueva, sin derivarla de datos locales.
UPDATE public.usuario
SET uid_global = gen_random_uuid()
WHERE uid_global IS NULL;

ALTER TABLE public.usuario
    ALTER COLUMN uid_global SET DEFAULT gen_random_uuid(),
    ALTER COLUMN uid_global SET NOT NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_catalog.pg_constraint
        WHERE conrelid = 'public.usuario'::regclass
          AND conname = 'uq_usuario_uid_global'
    ) THEN
        ALTER TABLE public.usuario
            ADD CONSTRAINT uq_usuario_uid_global UNIQUE (uid_global);
    ELSIF pg_catalog.pg_get_constraintdef((
        SELECT oid
        FROM pg_catalog.pg_constraint
        WHERE conrelid = 'public.usuario'::regclass
          AND conname = 'uq_usuario_uid_global'
    )) <> 'UNIQUE (uid_global)' THEN
        RAISE EXCEPTION 'uq_usuario_uid_global incompatible';
    END IF;
END $$;

CREATE OR REPLACE FUNCTION public.trg_usuario_uid_global_inmutable()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.uid_global IS DISTINCT FROM OLD.uid_global THEN
        RAISE EXCEPTION 'usuario.uid_global es inmutable';
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_bu_usuario_uid_global_inmutable ON public.usuario;
CREATE TRIGGER trg_bu_usuario_uid_global_inmutable
BEFORE UPDATE OF uid_global ON public.usuario
FOR EACH ROW
EXECUTE FUNCTION public.trg_usuario_uid_global_inmutable();

COMMIT;
