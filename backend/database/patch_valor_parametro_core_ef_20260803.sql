-- #410: preparación SQL CORE-EF de valor_parametro.
-- No crea definiciones, valores funcionales, API, outbox ni historial.
BEGIN;

LOCK TABLE public.valor_parametro IN ACCESS EXCLUSIVE MODE;

DO $$
DECLARE
    col record;
    expected text;
BEGIN
    IF to_regclass('public.valor_parametro') IS NULL
       OR to_regclass('public.parametro_sistema') IS NULL
       OR to_regclass('public.alcance_parametro') IS NULL
       OR to_regclass('public.instalacion') IS NULL THEN
        RAISE EXCEPTION 'faltan tablas requeridas para preparar valor_parametro';
    END IF;

    -- Una columna ya existente debe coincidir físicamente; no se corrige metadata parcial.
    FOR col IN
        SELECT * FROM (VALUES
            ('uid_global', 'uuid', true),
            ('version_registro', 'integer', true),
            ('created_at', 'timestamp without time zone', true),
            ('updated_at', 'timestamp without time zone', true),
            ('deleted_at', 'timestamp without time zone', false),
            ('id_instalacion_origen', 'bigint', false),
            ('id_instalacion_ultima_modificacion', 'bigint', false),
            ('op_id_alta', 'uuid', false),
            ('op_id_ultima_modificacion', 'uuid', false)
        ) AS x(name, data_type, required_not_null)
    LOOP
        SELECT format_type(a.atttypid, a.atttypmod)
          INTO expected
          FROM pg_attribute a
         WHERE a.attrelid = 'public.valor_parametro'::regclass
           AND a.attname = col.name AND NOT a.attisdropped;
        IF expected IS NOT NULL AND expected <> col.data_type THEN
            RAISE EXCEPTION 'columna valor_parametro.% incompatible: tipo %', col.name, expected;
        END IF;
    END LOOP;

    IF EXISTS (
        SELECT 1 FROM public.valor_parametro v
        LEFT JOIN public.parametro_sistema p USING (id_parametro_sistema)
        WHERE p.id_parametro_sistema IS NULL
    ) THEN RAISE EXCEPTION 'valor_parametro referencia definición inexistente'; END IF;

    IF EXISTS (
        SELECT 1 FROM public.valor_parametro v
        JOIN public.parametro_sistema p USING (id_parametro_sistema)
        JOIN public.alcance_parametro a USING (id_alcance_parametro)
        WHERE a.codigo_alcance = 'GLOBAL'
          AND (v.id_sucursal IS NOT NULL OR v.id_instalacion IS NOT NULL)
    ) THEN RAISE EXCEPTION 'valor GLOBAL con contexto incompatible'; END IF;

    IF EXISTS (SELECT 1 FROM public.valor_parametro
               WHERE fecha_desde IS NOT NULL AND fecha_hasta IS NOT NULL
                 AND fecha_hasta <= fecha_desde)
    THEN RAISE EXCEPTION 'vigencia de valor_parametro inválida'; END IF;

    IF EXISTS (
        SELECT 1 FROM public.valor_parametro
        WHERE id_sucursal IS NULL AND id_instalacion IS NULL AND es_valor_vigente
        GROUP BY id_parametro_sistema HAVING count(*) > 1
    ) THEN RAISE EXCEPTION 'más de un valor global vigente para una definición'; END IF;
END $$;

ALTER TABLE public.valor_parametro
    ADD COLUMN IF NOT EXISTS uid_global uuid,
    ADD COLUMN IF NOT EXISTS version_registro integer,
    ADD COLUMN IF NOT EXISTS created_at timestamp without time zone,
    ADD COLUMN IF NOT EXISTS updated_at timestamp without time zone,
    ADD COLUMN IF NOT EXISTS deleted_at timestamp without time zone,
    ADD COLUMN IF NOT EXISTS id_instalacion_origen bigint,
    ADD COLUMN IF NOT EXISTS id_instalacion_ultima_modificacion bigint,
    ADD COLUMN IF NOT EXISTS op_id_alta uuid,
    ADD COLUMN IF NOT EXISTS op_id_ultima_modificacion uuid;

-- Backfill conservador: sólo metadata técnica demostrable.
UPDATE public.valor_parametro
SET uid_global = COALESCE(uid_global, gen_random_uuid()),
    version_registro = COALESCE(version_registro, 1),
    created_at = COALESCE(created_at, CURRENT_TIMESTAMP),
    updated_at = COALESCE(updated_at, created_at, CURRENT_TIMESTAMP),
    deleted_at = deleted_at
WHERE uid_global IS NULL OR version_registro IS NULL
   OR created_at IS NULL OR updated_at IS NULL;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM public.valor_parametro WHERE version_registro <> 1) THEN
        RAISE EXCEPTION 'version_registro preexistente incompatible';
    END IF;
    IF EXISTS (SELECT uid_global FROM public.valor_parametro GROUP BY uid_global HAVING count(*) > 1) THEN
        RAISE EXCEPTION 'uid_global duplicado en valor_parametro';
    END IF;
    IF EXISTS (SELECT op_id_alta FROM public.valor_parametro WHERE op_id_alta IS NOT NULL GROUP BY op_id_alta HAVING count(*) > 1) THEN
        RAISE EXCEPTION 'op_id_alta duplicado incompatible en valor_parametro';
    END IF;
    IF EXISTS (SELECT 1 FROM public.valor_parametro v LEFT JOIN public.instalacion i ON i.id_instalacion=v.id_instalacion_origen
               WHERE v.id_instalacion_origen IS NOT NULL AND i.id_instalacion IS NULL)
       OR EXISTS (SELECT 1 FROM public.valor_parametro v LEFT JOIN public.instalacion i ON i.id_instalacion=v.id_instalacion_ultima_modificacion
               WHERE v.id_instalacion_ultima_modificacion IS NOT NULL AND i.id_instalacion IS NULL)
    THEN RAISE EXCEPTION 'procedencia de instalación inválida en valor_parametro'; END IF;
END $$;

ALTER TABLE public.valor_parametro
    ALTER COLUMN uid_global SET DEFAULT gen_random_uuid(),
    ALTER COLUMN uid_global SET NOT NULL,
    ALTER COLUMN version_registro SET DEFAULT 1,
    ALTER COLUMN version_registro SET NOT NULL,
    ALTER COLUMN created_at SET DEFAULT CURRENT_TIMESTAMP,
    ALTER COLUMN created_at SET NOT NULL,
    ALTER COLUMN updated_at SET DEFAULT CURRENT_TIMESTAMP,
    ALTER COLUMN updated_at SET NOT NULL;

-- La constraint histórica admitía fechas iguales; #410 exige orden estricto.
DO $$
DECLARE actual text;
BEGIN
    SELECT pg_get_constraintdef(oid) INTO actual FROM pg_constraint
     WHERE conrelid='public.valor_parametro'::regclass AND conname='chk_valor_parametro_vigencia';
    IF actual IS NOT NULL AND replace(actual, ' ', '') NOT LIKE '%fecha_hasta>fecha_desde%' THEN
        ALTER TABLE public.valor_parametro DROP CONSTRAINT chk_valor_parametro_vigencia;
    END IF;
END $$;

DO $$
DECLARE item record; actual text;
BEGIN
    FOR item IN SELECT * FROM (VALUES
      ('uq_valor_parametro_uid_global', 'UNIQUE (uid_global)'),
      ('chk_valor_parametro_version_registro', 'CHECK (version_registro >= 1)'),
      ('chk_valor_parametro_deleted_at', 'CHECK (deleted_at IS NULL OR deleted_at >= created_at)'),
      ('chk_valor_parametro_vigencia', 'CHECK (fecha_hasta IS NULL OR fecha_desde IS NULL OR fecha_hasta > fecha_desde)'),
      ('fk_valor_parametro_instalacion_origen', 'FOREIGN KEY (id_instalacion_origen) REFERENCES public.instalacion(id_instalacion) ON DELETE RESTRICT'),
      ('fk_valor_parametro_instalacion_ultima_modificacion', 'FOREIGN KEY (id_instalacion_ultima_modificacion) REFERENCES public.instalacion(id_instalacion) ON DELETE RESTRICT')
    ) AS x(name, definition)
    LOOP
      SELECT pg_get_constraintdef(oid) INTO actual FROM pg_constraint
       WHERE conrelid='public.valor_parametro'::regclass AND conname=item.name;
      IF actual IS NULL THEN
        EXECUTE format('ALTER TABLE public.valor_parametro ADD CONSTRAINT %I %s', item.name, item.definition);
      ELSIF regexp_replace(replace(actual, 'public.', ''), '[[:space:]()]|::[a-z ]+', '', 'g') <> regexp_replace(replace(item.definition, 'public.', ''), '[[:space:]()]|::[a-z ]+', '', 'g') THEN
        RAISE EXCEPTION 'constraint % incompatible: %', item.name, actual;
      END IF;
    END LOOP;
END $$;

DO $$
DECLARE actual text;
BEGIN
  SELECT indexdef INTO actual FROM pg_indexes WHERE schemaname='public' AND indexname='ux_valor_parametro_op_id_alta';
  IF actual IS NULL THEN
    CREATE UNIQUE INDEX ux_valor_parametro_op_id_alta ON public.valor_parametro(op_id_alta) WHERE op_id_alta IS NOT NULL;
  ELSIF regexp_replace(actual, '[[:space:]()]', '', 'g') <> 'CREATEUNIQUEINDEXux_valor_parametro_op_id_altaONpublic.valor_parametroUSINGbtreeop_id_altaWHEREop_id_altaISNOTNULL' THEN
    RAISE EXCEPTION 'índice ux_valor_parametro_op_id_alta incompatible';
  END IF;
  SELECT indexdef INTO actual FROM pg_indexes WHERE schemaname='public' AND indexname='ux_valor_parametro_global_vigente';
  IF actual IS NULL THEN
    CREATE UNIQUE INDEX ux_valor_parametro_global_vigente ON public.valor_parametro(id_parametro_sistema)
      WHERE id_sucursal IS NULL AND id_instalacion IS NULL AND es_valor_vigente AND deleted_at IS NULL;
  ELSIF regexp_replace(actual, '[[:space:]()]', '', 'g') <> 'CREATEUNIQUEINDEXux_valor_parametro_global_vigenteONpublic.valor_parametroUSINGbtreeid_parametro_sistemaWHEREid_sucursalISNULLANDid_instalacionISNULLANDes_valor_vigenteANDdeleted_atISNULL' THEN
    RAISE EXCEPTION 'índice ux_valor_parametro_global_vigente incompatible';
  END IF;
END $$;

CREATE OR REPLACE FUNCTION public.trg_valor_parametro_core_ef_insert() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
  IF NEW.uid_global IS NULL THEN NEW.uid_global := gen_random_uuid(); END IF;
  IF NEW.version_registro IS NULL THEN NEW.version_registro := 1; END IF;
  IF NEW.version_registro <> 1 THEN RAISE EXCEPTION 'valor_parametro debe iniciar en versión 1'; END IF;
  IF NEW.created_at IS NULL THEN NEW.created_at := CURRENT_TIMESTAMP; END IF;
  IF NEW.updated_at IS NULL THEN NEW.updated_at := NEW.created_at; END IF;
  IF NEW.id_instalacion_ultima_modificacion IS NULL THEN NEW.id_instalacion_ultima_modificacion := NEW.id_instalacion_origen; END IF;
  IF NEW.op_id_ultima_modificacion IS NULL THEN NEW.op_id_ultima_modificacion := NEW.op_id_alta; END IF;
  RETURN NEW;
END $$;

CREATE OR REPLACE FUNCTION public.trg_valor_parametro_core_ef_update() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
  NEW.uid_global := OLD.uid_global;
  NEW.created_at := OLD.created_at;
  NEW.id_instalacion_origen := OLD.id_instalacion_origen;
  NEW.op_id_alta := OLD.op_id_alta;
  NEW.updated_at := CURRENT_TIMESTAMP;
  NEW.version_registro := OLD.version_registro + 1;
  RETURN NEW;
END $$;

CREATE OR REPLACE FUNCTION public.trg_valor_parametro_validar_alcance() RETURNS trigger
LANGUAGE plpgsql AS $$
DECLARE codigo text;
BEGIN
  SELECT a.codigo_alcance INTO codigo
    FROM public.parametro_sistema p
    JOIN public.alcance_parametro a ON a.id_alcance_parametro=p.id_alcance_parametro
   WHERE p.id_parametro_sistema=NEW.id_parametro_sistema;
  IF NOT FOUND THEN RAISE EXCEPTION 'definición inexistente para valor_parametro'; END IF;
  IF codigo='GLOBAL' AND (NEW.id_sucursal IS NOT NULL OR NEW.id_instalacion IS NOT NULL) THEN
    RAISE EXCEPTION 'una definición GLOBAL no admite sucursal ni instalación';
  END IF;
  RETURN NEW;
END $$;

DO $$
DECLARE item record; actual text;
BEGIN
 FOR item IN SELECT * FROM (VALUES
  ('trg_bi_valor_parametro_core_ef','CREATE TRIGGER trg_bi_valor_parametro_core_ef BEFORE INSERT ON public.valor_parametro FOR EACH ROW EXECUTE FUNCTION public.trg_valor_parametro_core_ef_insert()'),
  ('trg_bu_valor_parametro_core_ef','CREATE TRIGGER trg_bu_valor_parametro_core_ef BEFORE UPDATE ON public.valor_parametro FOR EACH ROW EXECUTE FUNCTION public.trg_valor_parametro_core_ef_update()'),
  ('trg_biu_valor_parametro_validar_alcance','CREATE TRIGGER trg_biu_valor_parametro_validar_alcance BEFORE INSERT OR UPDATE ON public.valor_parametro FOR EACH ROW EXECUTE FUNCTION public.trg_valor_parametro_validar_alcance()')
 ) AS x(name, definition)
 LOOP
   SELECT pg_get_triggerdef(oid) INTO actual FROM pg_trigger WHERE tgrelid='public.valor_parametro'::regclass AND tgname=item.name AND NOT tgisinternal;
   IF actual IS NULL THEN EXECUTE item.definition;
   ELSIF regexp_replace(replace(actual, 'public.', ''), '[[:space:]]', '', 'g') <> regexp_replace(replace(item.definition, 'public.', ''), '[[:space:]]', '', 'g') THEN
     RAISE EXCEPTION 'trigger % incompatible: %', item.name, actual;
   END IF;
 END LOOP;
END $$;

-- Validación final dentro de la misma transacción.
DO $$
BEGIN
 IF EXISTS (SELECT 1 FROM public.valor_parametro WHERE uid_global IS NULL OR version_registro < 1 OR created_at IS NULL OR updated_at IS NULL)
 THEN RAISE EXCEPTION 'validación final CORE-EF fallida'; END IF;
END $$;

COMMIT;
