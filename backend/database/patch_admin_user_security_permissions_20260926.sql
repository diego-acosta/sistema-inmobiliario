-- Permisos D1 GLOBAL para administrar usuarios, grants y alcance por sucursal.
BEGIN;

DO $$
DECLARE
  missing_columns text;
BEGIN
  IF to_regclass('public.rol_seguridad') IS NULL
     OR to_regclass('public.permiso') IS NULL
     OR to_regclass('public.rol_seguridad_permiso') IS NULL THEN
    RAISE EXCEPTION
      'faltan tablas requeridas para materializar permisos administrativos';
  END IF;

  SELECT string_agg(required.column_name, ', ' ORDER BY required.column_name)
    INTO missing_columns
    FROM (VALUES
      ('rol_seguridad', 'id_rol_seguridad'),
      ('rol_seguridad', 'codigo_rol'),
      ('rol_seguridad', 'estado_rol'),
      ('permiso', 'id_permiso'),
      ('permiso', 'codigo_permiso'),
      ('permiso', 'nombre_permiso'),
      ('permiso', 'descripcion'),
      ('permiso', 'estado_permiso'),
      ('rol_seguridad_permiso', 'id_rol_seguridad'),
      ('rol_seguridad_permiso', 'id_permiso')
    ) AS required(table_name, column_name)
   WHERE NOT EXISTS (
     SELECT 1
       FROM information_schema.columns actual
      WHERE actual.table_schema = 'public'
        AND actual.table_name = required.table_name
        AND actual.column_name = required.column_name
   );

  IF missing_columns IS NOT NULL THEN
    RAISE EXCEPTION
      'faltan columnas requeridas para materializar permisos administrativos: %',
      missing_columns;
  END IF;
END $$;

LOCK TABLE public.rol_seguridad, public.permiso,
           public.rol_seguridad_permiso IN SHARE ROW EXCLUSIVE MODE;

DO $$
DECLARE
  role_count bigint;
  role_id bigint;
  permission_contract record;
  permission_count bigint;
  permission_id bigint;
  grant_count bigint;
BEGIN
  SELECT count(*), min(id_rol_seguridad)
    INTO role_count, role_id
    FROM public.rol_seguridad
   WHERE codigo_rol = 'ADMINISTRADOR_SISTEMA';

  IF role_count <> 1 THEN
    RAISE EXCEPTION
      'se requiere exactamente un rol ADMINISTRADOR_SISTEMA';
  END IF;

  IF NOT EXISTS (
    SELECT 1
      FROM public.rol_seguridad
     WHERE id_rol_seguridad = role_id
       AND estado_rol = 'ACTIVO'
  ) THEN
    RAISE EXCEPTION
      'el rol ADMINISTRADOR_SISTEMA debe estar ACTIVO';
  END IF;

  FOR permission_contract IN
    SELECT *
      FROM (VALUES
        (
          'ADMIN.USUARIO.ADMINISTRAR',
          'Administrar usuarios',
          'Permite crear y dar de baja usuarios del sistema.'
        ),
        (
          'ADMIN.SEGURIDAD.GRANTS.ADMINISTRAR',
          'Administrar grants de seguridad',
          'Permite asignar y revocar roles de seguridad de usuarios.'
        ),
        (
          'ADMIN.USUARIO_SUCURSAL.ADMINISTRAR',
          'Administrar alcance de usuarios por sucursal',
          'Permite asignar sucursales y capacidades operativas a usuarios.'
        )
      ) AS contract(codigo_permiso, nombre_permiso, descripcion)
  LOOP
    SELECT count(*), min(id_permiso)
      INTO permission_count, permission_id
      FROM public.permiso
     WHERE codigo_permiso = permission_contract.codigo_permiso;

    IF permission_count > 1 THEN
      RAISE EXCEPTION
        'cardinalidad incompatible del permiso %',
        permission_contract.codigo_permiso;
    END IF;

    IF permission_count = 1 AND NOT EXISTS (
      SELECT 1
        FROM public.permiso
       WHERE id_permiso = permission_id
         AND nombre_permiso = permission_contract.nombre_permiso
         AND descripcion = permission_contract.descripcion
         AND estado_permiso = 'ACTIVO'
    ) THEN
      RAISE EXCEPTION
        'permiso % preexistente incompatible',
        permission_contract.codigo_permiso;
    END IF;

    IF permission_count = 0 THEN
      INSERT INTO public.permiso (
        codigo_permiso,
        nombre_permiso,
        descripcion,
        estado_permiso
      ) VALUES (
        permission_contract.codigo_permiso,
        permission_contract.nombre_permiso,
        permission_contract.descripcion,
        'ACTIVO'
      )
      RETURNING id_permiso INTO permission_id;
    END IF;

    SELECT count(*)
      INTO grant_count
      FROM public.rol_seguridad_permiso
     WHERE id_rol_seguridad = role_id
       AND id_permiso = permission_id;

    IF grant_count > 1 THEN
      RAISE EXCEPTION
        'vínculo ADMINISTRADOR_SISTEMA/% duplicado',
        permission_contract.codigo_permiso;
    END IF;

    INSERT INTO public.rol_seguridad_permiso (
      id_rol_seguridad,
      id_permiso
    )
    SELECT role_id, permission_id
     WHERE grant_count = 0;
  END LOOP;
END $$;

COMMIT;
