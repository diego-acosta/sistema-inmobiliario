-- #448: contrato SQL CORE-EF inicial de credencial_usuario.
-- Sólo ALTER conservador sobre tabla histórica; no crea credenciales, runtime, outbox ni historial.
BEGIN;

LOCK TABLE public.credencial_usuario IN ACCESS EXCLUSIVE MODE;

DO $$
DECLARE
  col record; actual_type text; actual_nullable bool; actual_default text; actual text;
BEGIN
  IF to_regclass('public.credencial_usuario') IS NULL OR to_regclass('public.usuario') IS NULL OR to_regclass('public.instalacion') IS NULL THEN
    RAISE EXCEPTION 'faltan tablas requeridas para preparar credencial_usuario';
  END IF;

  FOR col IN SELECT * FROM (VALUES
    ('id_credencial_usuario','bigint',true,NULL),('id_usuario','bigint',true,NULL),
    ('tipo_credencial','character varying(50)',true,NULL),('identificador_credencial','character varying(150)',false,NULL),
    ('hash_credencial','text',true,NULL),('algoritmo_hash','character varying(100)',false,NULL),
    ('estado_credencial','character varying(30)',true,NULL),('es_credencial_principal','boolean',true,'false'),
    ('fecha_alta','timestamp without time zone',true,'CURRENT_TIMESTAMP'),('fecha_activacion','timestamp without time zone',false,NULL),
    ('fecha_vencimiento','timestamp without time zone',false,NULL),('fecha_revocacion','timestamp without time zone',false,NULL),
    ('motivo_revocacion','text',false,NULL),('obliga_rotacion','boolean',true,'false'),
    ('ultimo_cambio_credencial','timestamp without time zone',false,NULL),('intentos_fallidos_acumulados','integer',true,'0'),
    ('ultimo_intento_fallido','timestamp without time zone',false,NULL),('bloqueo_hasta','timestamp without time zone',false,NULL),
    ('requiere_reset','boolean',true,'false'),('observaciones','text',false,NULL)
  ) AS x(name, data_type, required_not_null, expected_default)
  LOOP
    SELECT format_type(a.atttypid,a.atttypmod), a.attnotnull, pg_get_expr(d.adbin,d.adrelid)
      INTO actual_type, actual_nullable, actual_default
      FROM pg_attribute a LEFT JOIN pg_attrdef d ON d.adrelid=a.attrelid AND d.adnum=a.attnum
     WHERE a.attrelid='public.credencial_usuario'::regclass AND a.attname=col.name AND NOT a.attisdropped;
    IF actual_type IS NULL OR actual_type <> col.data_type THEN RAISE EXCEPTION 'columna histórica credencial_usuario.% incompatible: %', col.name, actual_type; END IF;
    IF col.name <> 'algoritmo_hash' AND actual_nullable IS DISTINCT FROM col.required_not_null THEN RAISE EXCEPTION 'nullability histórica credencial_usuario.% incompatible', col.name; END IF;
    IF col.expected_default IS NOT NULL AND actual_default IS NOT NULL AND lower(regexp_replace(actual_default,'[[:space:]()]|::boolean|::integer','', 'g')) <> lower(col.expected_default) THEN
      RAISE EXCEPTION 'default histórico credencial_usuario.% incompatible: %', col.name, actual_default;
    END IF;
  END LOOP;

  SELECT pg_get_constraintdef(oid) INTO actual FROM pg_constraint WHERE conrelid='public.credencial_usuario'::regclass AND conname='credencial_usuario_pkey';
  IF actual IS NULL OR actual <> 'PRIMARY KEY (id_credencial_usuario)' THEN RAISE EXCEPTION 'PK credencial_usuario incompatible'; END IF;
  SELECT pg_get_constraintdef(oid) INTO actual FROM pg_constraint WHERE conrelid='public.credencial_usuario'::regclass AND conname='fk_cred_usuario';
  IF actual IS NULL OR actual NOT LIKE '%FOREIGN KEY (id_usuario) REFERENCES usuario(id_usuario)%ON DELETE RESTRICT%' THEN RAISE EXCEPTION 'FK histórica a usuario incompatible'; END IF;

  FOR col IN SELECT * FROM (VALUES
    ('uid_global','uuid',true,'gen_random_uuid()'),('version_registro','integer',true,'1'),
    ('created_at','timestamp without time zone',true,'CURRENT_TIMESTAMP'),('updated_at','timestamp without time zone',true,'CURRENT_TIMESTAMP'),
    ('deleted_at','timestamp without time zone',false,NULL),('id_instalacion_origen','bigint',false,NULL),
    ('id_instalacion_ultima_modificacion','bigint',false,NULL),('op_id_alta','uuid',false,NULL),('op_id_ultima_modificacion','uuid',false,NULL)
  ) AS x(name, data_type, required_not_null, expected_default)
  LOOP
    SELECT format_type(a.atttypid,a.atttypmod), a.attnotnull, pg_get_expr(d.adbin,d.adrelid)
      INTO actual_type, actual_nullable, actual_default
      FROM pg_attribute a LEFT JOIN pg_attrdef d ON d.adrelid=a.attrelid AND d.adnum=a.attnum
     WHERE a.attrelid='public.credencial_usuario'::regclass AND a.attname=col.name AND NOT a.attisdropped;
    IF actual_type IS NOT NULL THEN
      IF actual_type <> col.data_type THEN RAISE EXCEPTION 'metadata credencial_usuario.% tipo incompatible: %', col.name, actual_type; END IF;
      IF actual_nullable IS DISTINCT FROM col.required_not_null THEN RAISE EXCEPTION 'metadata credencial_usuario.% nullability incompatible', col.name; END IF;
      IF col.expected_default IS NOT NULL AND (actual_default IS NULL OR NOT (
        (col.name='uid_global' AND regexp_replace(actual_default,'[[:space:]]','','g')='gen_random_uuid()') OR
        (col.name='version_registro' AND regexp_replace(actual_default,'[[:space:]()]|::integer','','g')='1') OR
        (col.name IN ('created_at','updated_at') AND upper(regexp_replace(actual_default,'[[:space:]()]','','g')) IN ('CURRENT_TIMESTAMP','NOW'))
      )) THEN RAISE EXCEPTION 'metadata credencial_usuario.% default incompatible: %', col.name, actual_default; END IF;
    END IF;
  END LOOP;
END $$;

DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM public.credencial_usuario c LEFT JOIN public.usuario u ON u.id_usuario=c.id_usuario WHERE u.id_usuario IS NULL) THEN RAISE EXCEPTION 'credencial_usuario con usuario inexistente'; END IF;
  IF EXISTS (SELECT 1 FROM public.credencial_usuario WHERE hash_credencial IS NULL OR btrim(hash_credencial)='') THEN RAISE EXCEPTION 'hash_credencial nulo o vacío'; END IF;
  IF EXISTS (SELECT 1 FROM public.credencial_usuario WHERE algoritmo_hash IS NULL OR btrim(algoritmo_hash)='') THEN RAISE EXCEPTION 'algoritmo_hash nulo o vacío'; END IF;
  IF EXISTS (SELECT 1 FROM public.credencial_usuario WHERE tipo_credencial <> 'PASSWORD') THEN RAISE EXCEPTION 'tipo_credencial incompatible'; END IF;
  IF EXISTS (SELECT 1 FROM public.credencial_usuario WHERE estado_credencial NOT IN ('ACTIVA','REVOCADA')) THEN RAISE EXCEPTION 'estado_credencial incompatible'; END IF;
  IF EXISTS (SELECT 1 FROM public.credencial_usuario WHERE intentos_fallidos_acumulados < 0) THEN RAISE EXCEPTION 'contador de intentos incompatible'; END IF;
  IF EXISTS (SELECT 1 FROM public.credencial_usuario WHERE (estado_credencial='REVOCADA') <> (fecha_revocacion IS NOT NULL)) THEN RAISE EXCEPTION 'revocación incoherente'; END IF;
  IF EXISTS (SELECT 1 FROM public.credencial_usuario WHERE (fecha_activacion IS NOT NULL AND fecha_activacion < fecha_alta) OR (fecha_vencimiento IS NOT NULL AND fecha_activacion IS NOT NULL AND fecha_vencimiento <= fecha_activacion) OR (fecha_revocacion IS NOT NULL AND fecha_revocacion < fecha_alta) OR (fecha_revocacion IS NOT NULL AND fecha_activacion IS NOT NULL AND fecha_revocacion < fecha_activacion) OR (ultimo_cambio_credencial IS NOT NULL AND ultimo_cambio_credencial < fecha_alta) OR (ultimo_intento_fallido IS NOT NULL AND ultimo_intento_fallido < fecha_alta) OR (bloqueo_hasta IS NOT NULL AND ultimo_intento_fallido IS NOT NULL AND bloqueo_hasta < ultimo_intento_fallido)) THEN RAISE EXCEPTION 'fechas de credencial_usuario incompatibles'; END IF;
END $$;

ALTER TABLE public.credencial_usuario
  ADD COLUMN IF NOT EXISTS uid_global uuid,
  ADD COLUMN IF NOT EXISTS version_registro integer,
  ADD COLUMN IF NOT EXISTS created_at timestamp without time zone,
  ADD COLUMN IF NOT EXISTS updated_at timestamp without time zone,
  ADD COLUMN IF NOT EXISTS deleted_at timestamp without time zone,
  ADD COLUMN IF NOT EXISTS id_instalacion_origen bigint,
  ADD COLUMN IF NOT EXISTS id_instalacion_ultima_modificacion bigint,
  ADD COLUMN IF NOT EXISTS op_id_alta uuid,
  ADD COLUMN IF NOT EXISTS op_id_ultima_modificacion uuid;

UPDATE public.credencial_usuario
   SET uid_global=COALESCE(uid_global, gen_random_uuid()), version_registro=COALESCE(version_registro,1),
       created_at=COALESCE(created_at, fecha_alta, CURRENT_TIMESTAMP), updated_at=COALESCE(updated_at, created_at, fecha_alta, CURRENT_TIMESTAMP)
 WHERE uid_global IS NULL OR version_registro IS NULL OR created_at IS NULL OR updated_at IS NULL;

ALTER TABLE public.credencial_usuario
  ALTER COLUMN algoritmo_hash SET NOT NULL,
  ALTER COLUMN uid_global SET DEFAULT gen_random_uuid(), ALTER COLUMN uid_global SET NOT NULL,
  ALTER COLUMN version_registro SET DEFAULT 1, ALTER COLUMN version_registro SET NOT NULL,
  ALTER COLUMN created_at SET DEFAULT CURRENT_TIMESTAMP, ALTER COLUMN created_at SET NOT NULL,
  ALTER COLUMN updated_at SET DEFAULT CURRENT_TIMESTAMP, ALTER COLUMN updated_at SET NOT NULL;

DO $$
DECLARE item record; actual text;
BEGIN
 FOR item IN SELECT * FROM (VALUES
  ('uq_credencial_usuario_uid_global','UNIQUE (uid_global)'),
  ('chk_credencial_usuario_tipo_password','CHECK (tipo_credencial = ''PASSWORD'')'),
  ('chk_credencial_usuario_estado','CHECK (estado_credencial IN (''ACTIVA'', ''REVOCADA''))'),
  ('chk_credencial_usuario_hash_no_vacio','CHECK (btrim(hash_credencial) <> '''')'),
  ('chk_credencial_usuario_algoritmo_no_vacio','CHECK (btrim(algoritmo_hash) <> '''')'),
  ('chk_credencial_usuario_version_registro','CHECK (version_registro >= 1)'),
  ('chk_credencial_usuario_intentos_no_negativos','CHECK (intentos_fallidos_acumulados >= 0)'),
  ('chk_credencial_usuario_deleted_at','CHECK (deleted_at IS NULL OR deleted_at >= created_at)'),
  ('chk_credencial_usuario_fecha_activacion','CHECK (fecha_activacion IS NULL OR fecha_activacion >= fecha_alta)'),
  ('chk_credencial_usuario_fecha_vencimiento','CHECK (fecha_vencimiento IS NULL OR fecha_activacion IS NULL OR fecha_vencimiento > fecha_activacion)'),
  ('chk_credencial_usuario_fecha_revocacion_alta','CHECK (fecha_revocacion IS NULL OR fecha_revocacion >= fecha_alta)'),
  ('chk_credencial_usuario_fecha_revocacion_activacion','CHECK (fecha_revocacion IS NULL OR fecha_activacion IS NULL OR fecha_revocacion >= fecha_activacion)'),
  ('chk_credencial_usuario_revocacion_estado','CHECK ((estado_credencial = ''REVOCADA'') = (fecha_revocacion IS NOT NULL))'),
  ('chk_credencial_usuario_ultimo_cambio','CHECK (ultimo_cambio_credencial IS NULL OR ultimo_cambio_credencial >= fecha_alta)'),
  ('chk_credencial_usuario_ultimo_intento','CHECK (ultimo_intento_fallido IS NULL OR ultimo_intento_fallido >= fecha_alta)'),
  ('chk_credencial_usuario_bloqueo_hasta','CHECK (bloqueo_hasta IS NULL OR ultimo_intento_fallido IS NULL OR bloqueo_hasta >= ultimo_intento_fallido)'),
  ('fk_credencial_usuario_instalacion_origen','FOREIGN KEY (id_instalacion_origen) REFERENCES public.instalacion(id_instalacion) ON DELETE RESTRICT'),
  ('fk_credencial_usuario_instalacion_ultima_modificacion','FOREIGN KEY (id_instalacion_ultima_modificacion) REFERENCES public.instalacion(id_instalacion) ON DELETE RESTRICT')
 ) AS x(name, definition) LOOP
  SELECT pg_get_constraintdef(oid) INTO actual FROM pg_constraint WHERE conrelid='public.credencial_usuario'::regclass AND conname=item.name;
  IF actual IS NULL THEN EXECUTE format('ALTER TABLE public.credencial_usuario ADD CONSTRAINT %I %s', item.name, item.definition);
  ELSIF NOT (
      (item.name='chk_credencial_usuario_estado' AND actual LIKE '%ACTIVA%' AND actual LIKE '%REVOCADA%') OR
      regexp_replace(replace(actual,'public.',''),'[[:space:]()]|::[a-z ]+','','g') = regexp_replace(replace(item.definition,'public.',''),'[[:space:]()]|::[a-z ]+','','g')
    ) THEN
    RAISE EXCEPTION 'constraint % incompatible: %', item.name, actual;
  END IF;
 END LOOP;
END $$;

DO $$
DECLARE actual text;
BEGIN
  IF EXISTS (SELECT 1 FROM public.credencial_usuario GROUP BY uid_global HAVING count(*)>1) THEN RAISE EXCEPTION 'uid_global duplicado'; END IF;
  IF EXISTS (SELECT 1 FROM public.credencial_usuario WHERE op_id_alta IS NOT NULL GROUP BY op_id_alta HAVING count(*)>1) THEN RAISE EXCEPTION 'op_id_alta duplicado'; END IF;
  IF EXISTS (SELECT 1 FROM public.credencial_usuario c LEFT JOIN public.instalacion i ON i.id_instalacion=c.id_instalacion_origen WHERE c.id_instalacion_origen IS NOT NULL AND i.id_instalacion IS NULL)
     OR EXISTS (SELECT 1 FROM public.credencial_usuario c LEFT JOIN public.instalacion i ON i.id_instalacion=c.id_instalacion_ultima_modificacion WHERE c.id_instalacion_ultima_modificacion IS NOT NULL AND i.id_instalacion IS NULL) THEN RAISE EXCEPTION 'instalación de credencial_usuario inválida'; END IF;
  IF EXISTS (SELECT 1 FROM public.credencial_usuario WHERE estado_credencial='ACTIVA' AND deleted_at IS NULL GROUP BY id_usuario,tipo_credencial HAVING count(*)>1) THEN RAISE EXCEPTION 'credenciales activas duplicadas'; END IF;
  IF EXISTS (SELECT 1 FROM public.credencial_usuario WHERE es_credencial_principal IS TRUE AND estado_credencial='ACTIVA' AND deleted_at IS NULL GROUP BY id_usuario HAVING count(*)>1) THEN RAISE EXCEPTION 'credenciales principales activas duplicadas'; END IF;

  SELECT indexdef INTO actual FROM pg_indexes WHERE schemaname='public' AND indexname='ux_credencial_usuario_op_id_alta';
  IF actual IS NULL THEN CREATE UNIQUE INDEX ux_credencial_usuario_op_id_alta ON public.credencial_usuario(op_id_alta) WHERE op_id_alta IS NOT NULL;
  ELSIF regexp_replace(actual,'[[:space:]()]','','g') <> 'CREATEUNIQUEINDEXux_credencial_usuario_op_id_altaONpublic.credencial_usuarioUSINGbtreeop_id_altaWHEREop_id_altaISNOTNULL' THEN RAISE EXCEPTION 'índice ux_credencial_usuario_op_id_alta incompatible'; END IF;

  SELECT indexdef INTO actual FROM pg_indexes WHERE schemaname='public' AND indexname='ux_credencial_usuario_password_activa';
  IF actual IS NULL THEN CREATE UNIQUE INDEX ux_credencial_usuario_password_activa ON public.credencial_usuario(id_usuario,tipo_credencial) WHERE estado_credencial='ACTIVA' AND deleted_at IS NULL;
  ELSIF regexp_replace(actual,'[[:space:]()]|::text','','g') <> 'CREATEUNIQUEINDEXux_credencial_usuario_password_activaONpublic.credencial_usuarioUSINGbtreeid_usuario,tipo_credencialWHEREestado_credencial=''ACTIVA''ANDdeleted_atISNULL' THEN RAISE EXCEPTION 'índice ux_credencial_usuario_password_activa incompatible'; END IF;

  SELECT indexdef INTO actual FROM pg_indexes WHERE schemaname='public' AND indexname='ux_credencial_usuario_principal_activa';
  IF actual IS NULL THEN CREATE UNIQUE INDEX ux_credencial_usuario_principal_activa ON public.credencial_usuario(id_usuario) WHERE es_credencial_principal IS TRUE AND estado_credencial='ACTIVA' AND deleted_at IS NULL;
  ELSIF regexp_replace(actual,'[[:space:]()]|::text','','g') <> 'CREATEUNIQUEINDEXux_credencial_usuario_principal_activaONpublic.credencial_usuarioUSINGbtreeid_usuarioWHEREes_credencial_principalISTRUEANDestado_credencial=''ACTIVA''ANDdeleted_atISNULL' THEN RAISE EXCEPTION 'índice ux_credencial_usuario_principal_activa incompatible'; END IF;
END $$;

CREATE OR REPLACE FUNCTION public.trg_credencial_usuario_core_ef_insert()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  NEW.uid_global := COALESCE(NEW.uid_global, gen_random_uuid());
  NEW.version_registro := 1;
  NEW.created_at := COALESCE(NEW.created_at, CURRENT_TIMESTAMP);
  NEW.updated_at := COALESCE(NEW.updated_at, CURRENT_TIMESTAMP);
  NEW.id_instalacion_ultima_modificacion := COALESCE(NEW.id_instalacion_ultima_modificacion, NEW.id_instalacion_origen);
  NEW.op_id_ultima_modificacion := COALESCE(NEW.op_id_ultima_modificacion, NEW.op_id_alta);
  RETURN NEW;
END $$;

CREATE OR REPLACE FUNCTION public.trg_credencial_usuario_core_ef_update()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  NEW.uid_global := OLD.uid_global;
  NEW.created_at := OLD.created_at;
  NEW.id_instalacion_origen := OLD.id_instalacion_origen;
  NEW.op_id_alta := OLD.op_id_alta;
  NEW.updated_at := CURRENT_TIMESTAMP;
  NEW.version_registro := OLD.version_registro + 1;
  RETURN NEW;
END $$;

DO $$
DECLARE actual text;
BEGIN
  SELECT pg_get_triggerdef(oid) INTO actual FROM pg_trigger WHERE tgrelid='public.credencial_usuario'::regclass AND tgname='trg_bi_credencial_usuario_core_ef' AND NOT tgisinternal;
  IF actual IS NOT NULL AND actual NOT LIKE '%BEFORE INSERT%' THEN RAISE EXCEPTION 'trigger trg_bi_credencial_usuario_core_ef incompatible'; END IF;
  DROP TRIGGER IF EXISTS trg_bi_credencial_usuario_core_ef ON public.credencial_usuario;
  CREATE TRIGGER trg_bi_credencial_usuario_core_ef BEFORE INSERT ON public.credencial_usuario FOR EACH ROW EXECUTE FUNCTION public.trg_credencial_usuario_core_ef_insert();

  SELECT pg_get_triggerdef(oid) INTO actual FROM pg_trigger WHERE tgrelid='public.credencial_usuario'::regclass AND tgname='trg_bu_credencial_usuario_core_ef' AND NOT tgisinternal;
  IF actual IS NOT NULL AND actual NOT LIKE '%BEFORE UPDATE%' THEN RAISE EXCEPTION 'trigger trg_bu_credencial_usuario_core_ef incompatible'; END IF;
  DROP TRIGGER IF EXISTS trg_bu_credencial_usuario_core_ef ON public.credencial_usuario;
  CREATE TRIGGER trg_bu_credencial_usuario_core_ef BEFORE UPDATE ON public.credencial_usuario FOR EACH ROW EXECUTE FUNCTION public.trg_credencial_usuario_core_ef_update();
END $$;

COMMIT;
