BEGIN;

ALTER TABLE public.sesion_usuario
  ADD COLUMN IF NOT EXISTS uid_global uuid,
  ADD COLUMN IF NOT EXISTS version_registro integer,
  ADD COLUMN IF NOT EXISTS created_at timestamp without time zone,
  ADD COLUMN IF NOT EXISTS updated_at timestamp without time zone;

UPDATE public.sesion_usuario SET
  uid_global=COALESCE(uid_global,gen_random_uuid()),
  version_registro=COALESCE(version_registro,1),
  created_at=COALESCE(created_at,fecha_hora_inicio,CURRENT_TIMESTAMP),
  updated_at=COALESCE(updated_at,fecha_hora_inicio,CURRENT_TIMESTAMP)
WHERE uid_global IS NULL OR version_registro IS NULL OR created_at IS NULL OR updated_at IS NULL;

DO $$ BEGIN
  IF EXISTS (SELECT 1 FROM public.sesion_usuario WHERE token_sesion !~ '^[0-9a-f]{64}$') THEN
    RAISE EXCEPTION 'sesion_usuario contiene tokens incompatibles con digest SHA-256';
  END IF;
  IF EXISTS (SELECT 1 FROM public.sesion_usuario WHERE estado_sesion NOT IN ('ACTIVA','CERRADA','EXPIRADA')) THEN
    RAISE EXCEPTION 'sesion_usuario contiene estados incompatibles';
  END IF;
END $$;

ALTER TABLE public.sesion_usuario
  ALTER COLUMN uid_global SET DEFAULT gen_random_uuid(), ALTER COLUMN uid_global SET NOT NULL,
  ALTER COLUMN version_registro SET DEFAULT 1, ALTER COLUMN version_registro SET NOT NULL,
  ALTER COLUMN created_at SET DEFAULT CURRENT_TIMESTAMP, ALTER COLUMN created_at SET NOT NULL,
  ALTER COLUMN updated_at SET DEFAULT CURRENT_TIMESTAMP, ALTER COLUMN updated_at SET NOT NULL,
  ALTER COLUMN expira_en SET NOT NULL;

DO $$ DECLARE item record; BEGIN
 FOR item IN SELECT * FROM (VALUES
  ('uq_sesion_usuario_uid_global','UNIQUE (uid_global)'),
  ('chk_sesion_usuario_token_digest','CHECK (token_sesion ~ ''^[0-9a-f]{64}$'')'),
  ('chk_sesion_usuario_estado','CHECK (estado_sesion IN (''ACTIVA'',''CERRADA'',''EXPIRADA''))'),
  ('chk_sesion_usuario_estado_cierre','CHECK ((estado_sesion=''ACTIVA'' AND fecha_hora_cierre IS NULL) OR (estado_sesion IN (''CERRADA'',''EXPIRADA'') AND fecha_hora_cierre IS NOT NULL))'),
  ('chk_sesion_usuario_expiracion','CHECK (expira_en > fecha_hora_inicio)'),
  ('chk_sesion_usuario_actividad','CHECK (fecha_hora_ultima_actividad IS NULL OR fecha_hora_ultima_actividad >= fecha_hora_inicio)'),
  ('chk_sesion_usuario_version','CHECK (version_registro >= 1)')
 ) AS x(name, definition) LOOP
   IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid='public.sesion_usuario'::regclass AND conname=item.name) THEN
     EXECUTE format('ALTER TABLE public.sesion_usuario ADD CONSTRAINT %I %s',item.name,item.definition);
   END IF;
 END LOOP;
END $$;

CREATE INDEX IF NOT EXISTS ix_sesion_usuario_activa_expira
  ON public.sesion_usuario(expira_en) WHERE estado_sesion='ACTIVA';

COMMENT ON COLUMN public.sesion_usuario.token_sesion IS
  'Digest SHA-256 lowercase hex del bearer opaco; el bearer completo nunca se persiste.';
COMMENT ON TABLE public.sesion_usuario IS
  'Sesiones locales no sincronizables. Logout usa estado/cierre, nunca deleted_at.';

CREATE OR REPLACE FUNCTION public.trg_sesion_usuario_core_ef_insert() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 NEW.uid_global:=COALESCE(NEW.uid_global,gen_random_uuid()); NEW.version_registro:=1;
 NEW.created_at:=COALESCE(NEW.created_at,CURRENT_TIMESTAMP); NEW.updated_at:=COALESCE(NEW.updated_at,CURRENT_TIMESTAMP);
 RETURN NEW;
END $$;
CREATE OR REPLACE FUNCTION public.trg_sesion_usuario_core_ef_update() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 NEW.uid_global:=OLD.uid_global; NEW.created_at:=OLD.created_at;
 NEW.version_registro:=OLD.version_registro+1; NEW.updated_at:=CURRENT_TIMESTAMP; RETURN NEW;
END $$;
DROP TRIGGER IF EXISTS trg_bi_sesion_usuario_core_ef ON public.sesion_usuario;
CREATE TRIGGER trg_bi_sesion_usuario_core_ef BEFORE INSERT ON public.sesion_usuario FOR EACH ROW EXECUTE FUNCTION public.trg_sesion_usuario_core_ef_insert();
DROP TRIGGER IF EXISTS trg_bu_sesion_usuario_core_ef ON public.sesion_usuario;
CREATE TRIGGER trg_bu_sesion_usuario_core_ef BEFORE UPDATE ON public.sesion_usuario FOR EACH ROW EXECUTE FUNCTION public.trg_sesion_usuario_core_ef_update();

COMMIT;
