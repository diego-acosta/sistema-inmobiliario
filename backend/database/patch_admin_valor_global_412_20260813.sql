-- #412: permiso, receptor canónico y parámetro técnico controlado del command.
BEGIN;
LOCK TABLE public.rol_seguridad, public.permiso, public.rol_seguridad_permiso,
           public.parametro_sistema, public.valor_parametro IN SHARE ROW EXCLUSIVE MODE;

DO $$
DECLARE
  role_count bigint; role_id bigint; permission_count bigint; permission_id bigint;
  type_id bigint; scope_id bigint; parameter_count bigint; parameter_id bigint;
  value_count bigint;
BEGIN
  SELECT count(*), min(id_rol_seguridad) INTO role_count, role_id
    FROM public.rol_seguridad WHERE codigo_rol='ADMINISTRADOR_SISTEMA';
  IF role_count <> 1 THEN
    RAISE EXCEPTION 'se requiere exactamente un rol ADMINISTRADOR_SISTEMA';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM public.rol_seguridad WHERE id_rol_seguridad=role_id AND estado_rol='ACTIVO') THEN
    RAISE EXCEPTION 'el rol ADMINISTRADOR_SISTEMA debe estar ACTIVO';
  END IF;

  SELECT count(*), min(id_permiso) INTO permission_count, permission_id
    FROM public.permiso WHERE codigo_permiso='ADMIN.CONFIG.PARAMETRO_GLOBAL.MODIFICAR';
  IF permission_count > 1 THEN RAISE EXCEPTION 'cardinalidad incompatible del permiso #412'; END IF;
  IF permission_count = 1 AND NOT EXISTS (
    SELECT 1 FROM public.permiso WHERE id_permiso=permission_id
      AND nombre_permiso='Modificar valor global de parámetro'
      AND descripcion='Permite modificar un valor GLOBAL administrativo existente y elegible.'
      AND estado_permiso='ACTIVO'
  ) THEN RAISE EXCEPTION 'permiso #412 preexistente incompatible'; END IF;
  IF permission_count = 0 THEN
    INSERT INTO public.permiso(codigo_permiso,nombre_permiso,descripcion,estado_permiso)
    VALUES ('ADMIN.CONFIG.PARAMETRO_GLOBAL.MODIFICAR','Modificar valor global de parámetro',
            'Permite modificar un valor GLOBAL administrativo existente y elegible.','ACTIVO')
    RETURNING id_permiso INTO permission_id;
  END IF;

  IF (SELECT count(*) FROM public.rol_seguridad_permiso
      WHERE id_rol_seguridad=role_id AND id_permiso=permission_id) > 1 THEN
    RAISE EXCEPTION 'vínculo rol-permiso #412 duplicado';
  END IF;
  INSERT INTO public.rol_seguridad_permiso(id_rol_seguridad,id_permiso)
  SELECT role_id, permission_id WHERE NOT EXISTS (
    SELECT 1 FROM public.rol_seguridad_permiso
     WHERE id_rol_seguridad=role_id AND id_permiso=permission_id);

  SELECT count(*), min(id_tipo_dato_parametro) INTO role_count, type_id
    FROM public.tipo_dato_parametro WHERE codigo_tipo_dato='ENTERO';
  IF role_count <> 1 THEN RAISE EXCEPTION 'se requiere exactamente un tipo ENTERO'; END IF;
  SELECT count(*), min(id_alcance_parametro) INTO role_count, scope_id
    FROM public.alcance_parametro WHERE codigo_alcance='GLOBAL';
  IF role_count <> 1 THEN RAISE EXCEPTION 'se requiere exactamente un alcance GLOBAL'; END IF;

  SELECT count(*), min(id_parametro_sistema) INTO parameter_count, parameter_id
    FROM public.parametro_sistema WHERE codigo_parametro='PRUEBA_ADMIN_VALOR_GLOBAL_ENTERO';
  IF parameter_count > 1 THEN RAISE EXCEPTION 'cardinalidad incompatible del parámetro técnico #412'; END IF;
  IF parameter_count = 1 AND NOT EXISTS (
    SELECT 1 FROM public.parametro_sistema WHERE id_parametro_sistema=parameter_id
      AND id_tipo_dato_parametro=type_id AND id_alcance_parametro=scope_id
      AND exponible_api_administrativa=true AND es_sensible=false
      AND editable_administrativamente=true
  ) THEN RAISE EXCEPTION 'parámetro técnico #412 preexistente incompatible'; END IF;
  IF parameter_count = 0 THEN
    INSERT INTO public.parametro_sistema(
      id_tipo_dato_parametro,id_alcance_parametro,codigo_parametro,nombre_parametro,
      descripcion,exponible_api_administrativa,es_sensible,editable_administrativamente)
    VALUES (type_id,scope_id,'PRUEBA_ADMIN_VALOR_GLOBAL_ENTERO',
            'Prueba administrativa de valor global entero',
            'Parámetro técnico controlado para validar el command administrativo #412.',
            true,false,true) RETURNING id_parametro_sistema INTO parameter_id;
  END IF;

  SELECT count(*) INTO value_count FROM public.valor_parametro
   WHERE id_parametro_sistema=parameter_id AND id_sucursal IS NULL
     AND id_instalacion IS NULL AND es_valor_vigente=true AND deleted_at IS NULL;
  IF value_count > 1 THEN RAISE EXCEPTION 'cardinalidad incompatible del valor técnico #412'; END IF;
  IF value_count = 0 THEN
    INSERT INTO public.valor_parametro(id_parametro_sistema,valor_parametro,es_valor_vigente)
    VALUES(parameter_id,'15',true);
  END IF;
END $$;
COMMIT;
