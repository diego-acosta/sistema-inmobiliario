-- Bootstrap administrativo canónico vinculado a #249 y al alcance histórico de #260.
-- Sólo crea el receptor de permisos futuros; no implementa permiso ni runtime de #412.
BEGIN;

DO $$
DECLARE
    column_contract record;
BEGIN
    IF to_regclass('public.rol_seguridad') IS NULL THEN
        RAISE EXCEPTION 'falta tabla requerida public.rol_seguridad';
    END IF;

    FOR column_contract IN
        SELECT * FROM (VALUES
            ('id_rol_seguridad', 'bigint', true),
            ('codigo_rol', 'character varying(50)', true),
            ('nombre_rol', 'character varying(150)', true),
            ('descripcion', 'text', false),
            ('estado_rol', 'character varying(30)', true)
        ) AS expected(column_name, data_type, not_null)
    LOOP
        IF NOT EXISTS (
            SELECT 1
              FROM pg_attribute
             WHERE attrelid = 'public.rol_seguridad'::regclass
               AND attname = column_contract.column_name
               AND NOT attisdropped
               AND format_type(atttypid, atttypmod) = column_contract.data_type
               AND attnotnull = column_contract.not_null
        ) THEN
            RAISE EXCEPTION
                'columna public.rol_seguridad.% ausente o incompatible (tipo/nullability)',
                column_contract.column_name;
        END IF;
    END LOOP;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
         WHERE conrelid = 'public.rol_seguridad'::regclass
           AND contype = 'p'
           AND conkey = ARRAY[(SELECT attnum FROM pg_attribute
                                WHERE attrelid = 'public.rol_seguridad'::regclass
                                  AND attname = 'id_rol_seguridad')]::smallint[]
    ) THEN
        RAISE EXCEPTION 'public.rol_seguridad requiere PK exclusiva sobre id_rol_seguridad';
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
         WHERE conrelid = 'public.rol_seguridad'::regclass
           AND contype = 'u'
           AND conkey = ARRAY[(SELECT attnum FROM pg_attribute
                                WHERE attrelid = 'public.rol_seguridad'::regclass
                                  AND attname = 'codigo_rol')]::smallint[]
    ) THEN
        RAISE EXCEPTION 'public.rol_seguridad requiere UNIQUE exclusivo sobre codigo_rol';
    END IF;

    IF pg_get_serial_sequence('public.rol_seguridad', 'id_rol_seguridad') IS NULL THEN
        RAISE EXCEPTION 'public.rol_seguridad.id_rol_seguridad requiere secuencia/default compatible';
    END IF;
END $$;

LOCK TABLE public.rol_seguridad IN SHARE ROW EXCLUSIVE MODE;

DO $$
DECLARE
    matching_rows bigint;
BEGIN
    SELECT count(*) INTO matching_rows
      FROM public.rol_seguridad
     WHERE codigo_rol = 'ADMINISTRADOR_SISTEMA';

    IF matching_rows > 1 THEN
        RAISE EXCEPTION 'cardinalidad incompatible para rol ADMINISTRADOR_SISTEMA: % filas', matching_rows;
    END IF;

    IF matching_rows = 1 AND EXISTS (
        SELECT 1 FROM public.rol_seguridad
         WHERE codigo_rol = 'ADMINISTRADOR_SISTEMA'
           AND (
               nombre_rol IS DISTINCT FROM 'Administrador del sistema'
               OR descripcion IS DISTINCT FROM
                  'Rol administrativo global para la gestión y configuración del sistema.'
               OR estado_rol IS DISTINCT FROM 'ACTIVO'
           )
    ) THEN
        RAISE EXCEPTION 'rol ADMINISTRADOR_SISTEMA existente con contrato incompatible';
    END IF;

    IF matching_rows = 0 THEN
        INSERT INTO public.rol_seguridad (
            codigo_rol, nombre_rol, descripcion, estado_rol
        ) VALUES (
            'ADMINISTRADOR_SISTEMA',
            'Administrador del sistema',
            'Rol administrativo global para la gestión y configuración del sistema.',
            'ACTIVO'
        );
    END IF;
END $$;

COMMIT;
