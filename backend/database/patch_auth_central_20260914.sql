-- Auth/session/bootstrap central: columnas legacy conservadas, reloj UTC explícito.
BEGIN;
LOCK TABLE public.sesion_usuario, public.credencial_usuario IN ACCESS EXCLUSIVE MODE;

-- Validar sólo la frontera modificada; no reparar un schema incompatible.
DO $$
DECLARE item record;
BEGIN
  FOR item IN SELECT * FROM (VALUES
    ('sesion_usuario','id_instalacion_origen','bigint'),
    ('credencial_usuario','id_instalacion_origen','bigint'),
    ('credencial_usuario','id_instalacion_ultima_modificacion','bigint'),
    ('credencial_usuario','fecha_alta','timestamp without time zone'),
    ('sesion_usuario','created_at','timestamp without time zone'),
    ('sesion_usuario','updated_at','timestamp without time zone'),
    ('credencial_usuario','created_at','timestamp without time zone'),
    ('credencial_usuario','updated_at','timestamp without time zone')
  ) AS x(tabla,columna,tipo) LOOP
    IF NOT EXISTS (SELECT 1 FROM pg_attribute
      WHERE attrelid=('public.' || item.tabla)::regclass AND attname=item.columna
        AND NOT attisdropped AND attgenerated='' AND attidentity=''
        AND format_type(atttypid,atttypmod)=item.tipo) THEN
      RAISE EXCEPTION 'Estructura incompatible: %.%', item.tabla,item.columna;
    END IF;
  END LOOP;
  IF EXISTS (SELECT 1 FROM pg_attribute WHERE attrelid='public.credencial_usuario'::regclass
    AND attname IN ('id_instalacion_origen','id_instalacion_ultima_modificacion') AND attnotnull) THEN
    RAISE EXCEPTION 'Procedencia de credencial debe ser nullable conforme #448';
  END IF;
  FOR item IN SELECT * FROM (VALUES
    ('sesion_usuario','fk_sesion_inst','id_instalacion_origen'),
    ('credencial_usuario','fk_credencial_usuario_instalacion_origen','id_instalacion_origen'),
    ('credencial_usuario','fk_credencial_usuario_instalacion_ultima_modificacion','id_instalacion_ultima_modificacion')
  ) AS x(tabla,nombre,columna) LOOP
    IF NOT EXISTS (SELECT 1 FROM pg_constraint c
      JOIN pg_attribute a ON a.attrelid=c.conrelid AND a.attname=item.columna
      JOIN pg_attribute r ON r.attrelid=c.confrelid AND r.attname='id_instalacion'
      WHERE c.conrelid=('public.' || item.tabla)::regclass AND c.conname=item.nombre
        AND c.contype='f' AND c.confrelid='public.instalacion'::regclass
        AND c.conkey=ARRAY[a.attnum] AND c.confkey=ARRAY[r.attnum]
        AND c.confdeltype='r' AND c.convalidated) THEN
      RAISE EXCEPTION 'FK legacy incompatible: %',item.nombre;
    END IF;
  END LOOP;
END $$;

-- Comparación completa: sólo terminadores de línea y whitespace exterior.
DO $check$
DECLARE body text;
BEGIN
  SELECT prosrc INTO body FROM pg_proc WHERE oid=to_regprocedure('public.trg_sesion_usuario_core_ef_insert()')
    AND prorettype='trigger'::regtype AND NOT prosecdef;
  IF body IS NULL OR btrim(replace(replace(body, E'\r\n', E'\n'), E'\r', E'\n'), E' \t\n\r') NOT IN (btrim(replace(replace($old$
BEGIN
 NEW.uid_global:=COALESCE(NEW.uid_global,gen_random_uuid()); NEW.version_registro:=1;
 NEW.created_at:=COALESCE(NEW.created_at,CURRENT_TIMESTAMP); NEW.updated_at:=COALESCE(NEW.updated_at,CURRENT_TIMESTAMP);
 RETURN NEW;
END $old$, E'\r\n', E'\n'), E'\r', E'\n'), E' \t\n\r'),btrim(replace(replace($new$
BEGIN
 NEW.uid_global:=COALESCE(NEW.uid_global,gen_random_uuid()); NEW.version_registro:=1;
 NEW.created_at:=COALESCE(NEW.created_at,(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')); NEW.updated_at:=COALESCE(NEW.updated_at,(CURRENT_TIMESTAMP AT TIME ZONE 'UTC'));
 RETURN NEW;
END $new$, E'\r\n', E'\n'), E'\r', E'\n'), E' \t\n\r')) THEN
    RAISE EXCEPTION 'Función incompatible: trg_sesion_usuario_core_ef_insert';
  END IF;
END $check$;

DO $check$
DECLARE body text;
BEGIN
  SELECT prosrc INTO body FROM pg_proc WHERE oid=to_regprocedure('public.trg_sesion_usuario_core_ef_update()')
    AND prorettype='trigger'::regtype AND NOT prosecdef;
  IF body IS NULL OR btrim(replace(replace(body, E'\r\n', E'\n'), E'\r', E'\n'), E' \t\n\r') NOT IN (btrim(replace(replace($old$
BEGIN
 NEW.uid_global:=OLD.uid_global; NEW.created_at:=OLD.created_at;
 NEW.version_registro:=OLD.version_registro+1; NEW.updated_at:=CURRENT_TIMESTAMP; RETURN NEW;
END $old$, E'\r\n', E'\n'), E'\r', E'\n'), E' \t\n\r'),btrim(replace(replace($new$
BEGIN
 NEW.uid_global:=OLD.uid_global; NEW.created_at:=OLD.created_at;
 NEW.version_registro:=OLD.version_registro+1; NEW.updated_at:=(CURRENT_TIMESTAMP AT TIME ZONE 'UTC'); RETURN NEW;
END $new$, E'\r\n', E'\n'), E'\r', E'\n'), E' \t\n\r')) THEN
    RAISE EXCEPTION 'Función incompatible: trg_sesion_usuario_core_ef_update';
  END IF;
END $check$;

DO $check$
DECLARE body text;
BEGIN
  SELECT prosrc INTO body FROM pg_proc WHERE oid=to_regprocedure('public.trg_credencial_usuario_core_ef_insert()')
    AND prorettype='trigger'::regtype AND NOT prosecdef;
  IF body IS NULL OR btrim(replace(replace(body, E'\r\n', E'\n'), E'\r', E'\n'), E' \t\n\r') NOT IN (btrim(replace(replace($old$
BEGIN
  NEW.uid_global := COALESCE(NEW.uid_global, gen_random_uuid());
  NEW.version_registro := 1;
  NEW.created_at := COALESCE(NEW.created_at, CURRENT_TIMESTAMP);
  NEW.updated_at := COALESCE(NEW.updated_at, CURRENT_TIMESTAMP);
  NEW.id_instalacion_ultima_modificacion := COALESCE(NEW.id_instalacion_ultima_modificacion, NEW.id_instalacion_origen);
  NEW.op_id_ultima_modificacion := COALESCE(NEW.op_id_ultima_modificacion, NEW.op_id_alta);
  RETURN NEW;
END $old$, E'\r\n', E'\n'), E'\r', E'\n'), E' \t\n\r'),btrim(replace(replace($new$
BEGIN
  NEW.uid_global := COALESCE(NEW.uid_global, gen_random_uuid());
  NEW.version_registro := 1;
  NEW.created_at := COALESCE(NEW.created_at, (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'));
  NEW.updated_at := COALESCE(NEW.updated_at, (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'));
  NEW.id_instalacion_ultima_modificacion := COALESCE(NEW.id_instalacion_ultima_modificacion, NEW.id_instalacion_origen);
  NEW.op_id_ultima_modificacion := COALESCE(NEW.op_id_ultima_modificacion, NEW.op_id_alta);
  RETURN NEW;
END $new$, E'\r\n', E'\n'), E'\r', E'\n'), E' \t\n\r')) THEN
    RAISE EXCEPTION 'Función incompatible: trg_credencial_usuario_core_ef_insert';
  END IF;
END $check$;

DO $check$
DECLARE body text;
BEGIN
  SELECT prosrc INTO body FROM pg_proc WHERE oid=to_regprocedure('public.trg_credencial_usuario_core_ef_update()')
    AND prorettype='trigger'::regtype AND NOT prosecdef;
  IF body IS NULL OR btrim(replace(replace(body, E'\r\n', E'\n'), E'\r', E'\n'), E' \t\n\r') NOT IN (btrim(replace(replace($old$
BEGIN
  NEW.uid_global := OLD.uid_global;
  NEW.created_at := OLD.created_at;
  NEW.id_instalacion_origen := OLD.id_instalacion_origen;
  NEW.op_id_alta := OLD.op_id_alta;
  NEW.updated_at := CURRENT_TIMESTAMP;
  NEW.version_registro := OLD.version_registro + 1;
  RETURN NEW;
END $old$, E'\r\n', E'\n'), E'\r', E'\n'), E' \t\n\r'),btrim(replace(replace($new$
BEGIN
  NEW.uid_global := OLD.uid_global;
  NEW.created_at := OLD.created_at;
  NEW.id_instalacion_origen := OLD.id_instalacion_origen;
  NEW.op_id_alta := OLD.op_id_alta;
  NEW.updated_at := (CURRENT_TIMESTAMP AT TIME ZONE 'UTC');
  NEW.version_registro := OLD.version_registro + 1;
  RETURN NEW;
END $new$, E'\r\n', E'\n'), E'\r', E'\n'), E' \t\n\r')) THEN
    RAISE EXCEPTION 'Función incompatible: trg_credencial_usuario_core_ef_update';
  END IF;
END $check$;

ALTER TABLE public.sesion_usuario ALTER COLUMN id_instalacion_origen DROP NOT NULL;
ALTER TABLE public.sesion_usuario
  ALTER COLUMN created_at SET DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'),
  ALTER COLUMN updated_at SET DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC');
ALTER TABLE public.credencial_usuario
  ALTER COLUMN fecha_alta SET DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'),
  ALTER COLUMN created_at SET DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'),
  ALTER COLUMN updated_at SET DEFAULT (CURRENT_TIMESTAMP AT TIME ZONE 'UTC');

CREATE OR REPLACE FUNCTION public.trg_sesion_usuario_core_ef_insert() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 NEW.uid_global:=COALESCE(NEW.uid_global,gen_random_uuid()); NEW.version_registro:=1;
 NEW.created_at:=COALESCE(NEW.created_at,(CURRENT_TIMESTAMP AT TIME ZONE 'UTC')); NEW.updated_at:=COALESCE(NEW.updated_at,(CURRENT_TIMESTAMP AT TIME ZONE 'UTC'));
 RETURN NEW;
END $$;

CREATE OR REPLACE FUNCTION public.trg_sesion_usuario_core_ef_update() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
 NEW.uid_global:=OLD.uid_global; NEW.created_at:=OLD.created_at;
 NEW.version_registro:=OLD.version_registro+1; NEW.updated_at:=(CURRENT_TIMESTAMP AT TIME ZONE 'UTC'); RETURN NEW;
END $$;

CREATE OR REPLACE FUNCTION public.trg_credencial_usuario_core_ef_insert() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  NEW.uid_global := COALESCE(NEW.uid_global, gen_random_uuid());
  NEW.version_registro := 1;
  NEW.created_at := COALESCE(NEW.created_at, (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'));
  NEW.updated_at := COALESCE(NEW.updated_at, (CURRENT_TIMESTAMP AT TIME ZONE 'UTC'));
  NEW.id_instalacion_ultima_modificacion := COALESCE(NEW.id_instalacion_ultima_modificacion, NEW.id_instalacion_origen);
  NEW.op_id_ultima_modificacion := COALESCE(NEW.op_id_ultima_modificacion, NEW.op_id_alta);
  RETURN NEW;
END $$;

CREATE OR REPLACE FUNCTION public.trg_credencial_usuario_core_ef_update() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  NEW.uid_global := OLD.uid_global;
  NEW.created_at := OLD.created_at;
  NEW.id_instalacion_origen := OLD.id_instalacion_origen;
  NEW.op_id_alta := OLD.op_id_alta;
  NEW.updated_at := (CURRENT_TIMESTAMP AT TIME ZONE 'UTC');
  NEW.version_registro := OLD.version_registro + 1;
  RETURN NEW;
END $$;

COMMENT ON COLUMN public.sesion_usuario.id_instalacion_origen IS
  'Compatibilidad legacy nullable; sesiones centrales no requieren instalación.';
COMMENT ON TABLE public.sesion_usuario IS
  'Sesiones centrales revocables no sincronizables; timestamps UTC, bearer sólo digest.';
COMMIT;
