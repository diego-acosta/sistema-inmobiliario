-- Permiso D1 GLOBAL para administrar catalogos maestros e items configurables.
BEGIN;

LOCK TABLE public.rol_seguridad, public.permiso,
           public.rol_seguridad_permiso IN SHARE ROW EXCLUSIVE MODE;

DO $$
DECLARE
  role_count bigint;
  role_id bigint;
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

  SELECT count(*), min(id_permiso)
    INTO permission_count, permission_id
    FROM public.permiso
   WHERE codigo_permiso = 'ADMIN.CONFIG.CATALOGO.ADMINISTRAR';

  IF permission_count > 1 THEN
    RAISE EXCEPTION
      'cardinalidad incompatible del permiso ADMIN.CONFIG.CATALOGO.ADMINISTRAR';
  END IF;

  IF permission_count = 1 AND NOT EXISTS (
    SELECT 1
      FROM public.permiso
     WHERE id_permiso = permission_id
       AND nombre_permiso = 'Administrar catálogos'
       AND descripcion = 'Permite crear, modificar, cambiar estado y dar de baja catálogos maestros y sus ítems configurables.'
       AND estado_permiso = 'ACTIVO'
  ) THEN
    RAISE EXCEPTION
      'permiso ADMIN.CONFIG.CATALOGO.ADMINISTRAR preexistente incompatible';
  END IF;

  IF permission_count = 0 THEN
    INSERT INTO public.permiso (
      codigo_permiso,
      nombre_permiso,
      descripcion,
      estado_permiso
    ) VALUES (
      'ADMIN.CONFIG.CATALOGO.ADMINISTRAR',
      'Administrar catálogos',
      'Permite crear, modificar, cambiar estado y dar de baja catálogos maestros y sus ítems configurables.',
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
      'vínculo ADMINISTRADOR_SISTEMA/ADMIN.CONFIG.CATALOGO.ADMINISTRAR duplicado';
  END IF;

  INSERT INTO public.rol_seguridad_permiso (
    id_rol_seguridad,
    id_permiso
  )
  SELECT role_id, permission_id
   WHERE grant_count = 0;
END $$;

COMMIT;
