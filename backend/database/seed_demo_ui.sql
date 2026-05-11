-- SEED DEMO UI
--
-- Seed opcional para bases dev. No reemplaza seed_minimo.sql ni datos de tests.
-- Usa codigos prefijados DEMO y evita crear duplicados al reejecutarse.

DO $$
DECLARE
    v_op_id constant uuid := '22222222-2222-2222-2222-222222222222'::uuid;

    v_comprador bigint;
    v_locatario bigint;
    v_locador bigint;
    v_garante bigint;
    v_responsable_servicio bigint;
    v_persona_juridica bigint;

    v_rol_comprador bigint;
    v_rol_locatario bigint;
    v_rol_locador bigint;
    v_rol_garante bigint;

    v_inm_casa bigint;
    v_inm_edificio bigint;
    v_inm_lote bigint;
    v_uf_1a bigint;
    v_uf_1b bigint;
    v_uf_2a bigint;
    v_uf_deposito bigint;

    v_srv_agua bigint;
    v_srv_luz bigint;
    v_srv_gas bigint;
    v_srv_expensas bigint;

    v_reserva_loc bigint;
    v_contrato bigint;

    v_reserva_contado bigint;
    v_reserva_anticipo bigint;
    v_reserva_cuotas bigint;
    v_venta_contado bigint;
    v_venta_anticipo bigint;
    v_venta_cuotas bigint;
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM public.sucursal WHERE id_sucursal = 1 AND deleted_at IS NULL
    ) OR NOT EXISTS (
        SELECT 1 FROM public.instalacion WHERE id_instalacion = 1 AND deleted_at IS NULL
    ) THEN
        RAISE EXCEPTION 'seed_demo_ui.sql requiere baseline tecnico previo con sucursal=1 e instalacion=1';
    END IF;

    INSERT INTO public.rol_participacion (
        id_instalacion_origen, id_instalacion_ultima_modificacion,
        op_id_alta, op_id_ultima_modificacion,
        codigo_rol, nombre_rol, descripcion, estado_rol
    )
    VALUES
        (1, 1, v_op_id, v_op_id, 'COMPRADOR', 'Comprador', 'Rol comercial para ventas demo UI', 'ACTIVO'),
        (1, 1, v_op_id, v_op_id, 'LOCATARIO', 'Locatario', 'Rol locativo para contratos demo UI', 'ACTIVO'),
        (1, 1, v_op_id, v_op_id, 'LOCADOR', 'Locador', 'Rol locativo para contratos demo UI', 'ACTIVO'),
        (1, 1, v_op_id, v_op_id, 'GARANTE', 'Garante', 'Rol locativo para contratos demo UI', 'ACTIVO')
    ON CONFLICT (codigo_rol) DO UPDATE SET
        nombre_rol = EXCLUDED.nombre_rol,
        descripcion = EXCLUDED.descripcion,
        estado_rol = EXCLUDED.estado_rol,
        op_id_ultima_modificacion = EXCLUDED.op_id_ultima_modificacion;

    SELECT id_rol_participacion INTO v_rol_comprador FROM public.rol_participacion WHERE codigo_rol = 'COMPRADOR';
    SELECT id_rol_participacion INTO v_rol_locatario FROM public.rol_participacion WHERE codigo_rol = 'LOCATARIO';
    SELECT id_rol_participacion INTO v_rol_locador FROM public.rol_participacion WHERE codigo_rol = 'LOCADOR';
    SELECT id_rol_participacion INTO v_rol_garante FROM public.rol_participacion WHERE codigo_rol = 'GARANTE';

    INSERT INTO public.persona (
        id_instalacion_origen, id_instalacion_ultima_modificacion,
        op_id_alta, op_id_ultima_modificacion,
        tipo_persona, codigo_persona, apellido, nombre, razon_social, nombre_fantasia,
        estado_persona, fecha_nacimiento_constitucion, cuit_cuil,
        nacionalidad, fecha_alta, observaciones
    )
    VALUES
        (1, 1, v_op_id, v_op_id, 'FISICA', 'DEMO-PER-COMPRADOR', 'Compradora', 'Julia Demo', NULL, NULL, 'ACTIVA', DATE '1985-04-15', '20-90000001-1', 'Argentina', DATE '2026-01-01', 'DEMO UI comprador'),
        (1, 1, v_op_id, v_op_id, 'FISICA', 'DEMO-PER-LOCATARIO', 'Locatario', 'Martin Demo', NULL, NULL, 'ACTIVA', DATE '1990-08-22', '20-90000002-2', 'Argentina', DATE '2026-01-01', 'DEMO UI locatario'),
        (1, 1, v_op_id, v_op_id, 'FISICA', 'DEMO-PER-LOCADOR', 'Locadora', 'Ana Demo', NULL, NULL, 'ACTIVA', DATE '1978-03-10', '20-90000003-3', 'Argentina', DATE '2026-01-01', 'DEMO UI locador'),
        (1, 1, v_op_id, v_op_id, 'FISICA', 'DEMO-PER-GARANTE', 'Garante', 'Roberto Demo', NULL, NULL, 'ACTIVA', DATE '1980-11-30', '20-90000004-4', 'Argentina', DATE '2026-01-01', 'DEMO UI garante'),
        (1, 1, v_op_id, v_op_id, 'FISICA', 'DEMO-PER-RESP-SERV', 'Servicios', 'Carolina Demo', NULL, NULL, 'ACTIVA', DATE '1988-05-05', '20-90000005-5', 'Argentina', DATE '2026-01-01', 'DEMO UI responsable de servicio'),
        (1, 1, v_op_id, v_op_id, 'JURIDICA', 'DEMO-PER-JURIDICA', NULL, NULL, 'Demo Propiedades SA', 'Demo Propiedades', 'ACTIVA', DATE '2020-02-01', '30-90000006-6', 'Argentina', DATE '2026-01-01', 'DEMO UI persona juridica')
    ON CONFLICT (codigo_persona) DO UPDATE SET
        tipo_persona = EXCLUDED.tipo_persona,
        apellido = EXCLUDED.apellido,
        nombre = EXCLUDED.nombre,
        razon_social = EXCLUDED.razon_social,
        nombre_fantasia = EXCLUDED.nombre_fantasia,
        estado_persona = EXCLUDED.estado_persona,
        cuit_cuil = EXCLUDED.cuit_cuil,
        observaciones = EXCLUDED.observaciones,
        op_id_ultima_modificacion = EXCLUDED.op_id_ultima_modificacion;

    SELECT id_persona INTO v_comprador FROM public.persona WHERE codigo_persona = 'DEMO-PER-COMPRADOR';
    SELECT id_persona INTO v_locatario FROM public.persona WHERE codigo_persona = 'DEMO-PER-LOCATARIO';
    SELECT id_persona INTO v_locador FROM public.persona WHERE codigo_persona = 'DEMO-PER-LOCADOR';
    SELECT id_persona INTO v_garante FROM public.persona WHERE codigo_persona = 'DEMO-PER-GARANTE';
    SELECT id_persona INTO v_responsable_servicio FROM public.persona WHERE codigo_persona = 'DEMO-PER-RESP-SERV';
    SELECT id_persona INTO v_persona_juridica FROM public.persona WHERE codigo_persona = 'DEMO-PER-JURIDICA';

    INSERT INTO public.persona_documento (
        id_instalacion_origen, id_instalacion_ultima_modificacion,
        op_id_alta, op_id_ultima_modificacion,
        id_persona, tipo_documento_persona, numero_documento, pais_emision,
        es_principal, fecha_desde, observaciones
    )
    SELECT 1, 1, v_op_id, v_op_id, x.id_persona, x.tipo_documento, x.numero_documento,
           'Argentina', true, DATE '2026-01-01', 'DEMO UI documento principal'
    FROM (VALUES
        (v_comprador, 'DNI', '90000001'),
        (v_locatario, 'DNI', '90000002'),
        (v_locador, 'DNI', '90000003'),
        (v_garante, 'DNI', '90000004'),
        (v_responsable_servicio, 'DNI', '90000005'),
        (v_persona_juridica, 'CUIT', '30-90000006-6')
    ) AS x(id_persona, tipo_documento, numero_documento)
    WHERE NOT EXISTS (
        SELECT 1
        FROM public.persona_documento pd
        WHERE pd.tipo_documento_persona = x.tipo_documento
          AND pd.numero_documento = x.numero_documento
          AND pd.deleted_at IS NULL
    );

    INSERT INTO public.persona_contacto (
        id_instalacion_origen, id_instalacion_ultima_modificacion,
        op_id_alta, op_id_ultima_modificacion,
        id_persona, tipo_contacto, valor_contacto, es_principal, fecha_desde, observaciones
    )
    SELECT 1, 1, v_op_id, v_op_id, x.id_persona, 'EMAIL', x.email, true, DATE '2026-01-01', 'DEMO UI contacto principal'
    FROM (VALUES
        (v_comprador, 'comprador.demo@example.com'),
        (v_locatario, 'locatario.demo@example.com'),
        (v_locador, 'locador.demo@example.com'),
        (v_garante, 'garante.demo@example.com'),
        (v_responsable_servicio, 'servicios.demo@example.com'),
        (v_persona_juridica, 'administracion.demo@example.com')
    ) AS x(id_persona, email)
    WHERE NOT EXISTS (
        SELECT 1
        FROM public.persona_contacto pc
        WHERE pc.id_persona = x.id_persona
          AND pc.tipo_contacto = 'EMAIL'
          AND pc.es_principal = true
          AND pc.deleted_at IS NULL
    )
      AND NOT EXISTS (
        SELECT 1
        FROM public.persona_contacto pc
        WHERE pc.tipo_contacto = 'EMAIL'
          AND pc.valor_contacto = x.email
          AND pc.deleted_at IS NULL
    );

    INSERT INTO public.persona_domicilio (
        id_instalacion_origen, id_instalacion_ultima_modificacion,
        op_id_alta, op_id_ultima_modificacion,
        id_persona, tipo_domicilio, direccion, localidad, provincia, pais,
        codigo_postal, es_principal, fecha_desde, observaciones
    )
    SELECT 1, 1, v_op_id, v_op_id, x.id_persona, 'REAL', x.direccion,
           'Ciudad Demo', 'Buenos Aires', 'Argentina', '1000', true, DATE '2026-01-01',
           'DEMO UI domicilio principal'
    FROM (VALUES
        (v_comprador, 'Av. Demo 101'),
        (v_locatario, 'Calle Demo 202'),
        (v_locador, 'Pasaje Demo 303'),
        (v_garante, 'Diagonal Demo 404'),
        (v_responsable_servicio, 'Servicios Demo 505'),
        (v_persona_juridica, 'Oficina Demo 606')
    ) AS x(id_persona, direccion)
    WHERE NOT EXISTS (
        SELECT 1
        FROM public.persona_domicilio pd
        WHERE pd.id_persona = x.id_persona
          AND pd.es_principal = true
          AND pd.deleted_at IS NULL
    );

    INSERT INTO public.inmueble (
        id_instalacion_origen, id_instalacion_ultima_modificacion,
        op_id_alta, op_id_ultima_modificacion,
        codigo_inmueble, nombre_inmueble, superficie,
        estado_administrativo, estado_juridico, fecha_alta, observaciones
    )
    VALUES
        (1, 1, v_op_id, v_op_id, 'DEMO-INM-CASA-001', 'Casa Demo Palermo', 220.00, 'ACTIVO', 'REGULAR', DATE '2026-01-01', 'DEMO UI inmueble con disponibilidad normal'),
        (1, 1, v_op_id, v_op_id, 'DEMO-INM-EDIF-001', 'Edificio Demo Centro', 980.00, 'ACTIVO', 'REGULAR', DATE '2026-01-01', 'DEMO UI inmueble con estados ambiguos'),
        (1, 1, v_op_id, v_op_id, 'DEMO-INM-LOTE-001', 'Lote Demo Costa', 500.00, 'ACTIVO', 'EN_TRAMITE', DATE '2026-01-01', 'DEMO UI inmueble sin vigencia abierta')
    ON CONFLICT (codigo_inmueble) DO UPDATE SET
        nombre_inmueble = EXCLUDED.nombre_inmueble,
        superficie = EXCLUDED.superficie,
        estado_administrativo = EXCLUDED.estado_administrativo,
        estado_juridico = EXCLUDED.estado_juridico,
        observaciones = EXCLUDED.observaciones,
        op_id_ultima_modificacion = EXCLUDED.op_id_ultima_modificacion;

    SELECT id_inmueble INTO v_inm_casa FROM public.inmueble WHERE codigo_inmueble = 'DEMO-INM-CASA-001';
    SELECT id_inmueble INTO v_inm_edificio FROM public.inmueble WHERE codigo_inmueble = 'DEMO-INM-EDIF-001';
    SELECT id_inmueble INTO v_inm_lote FROM public.inmueble WHERE codigo_inmueble = 'DEMO-INM-LOTE-001';

    INSERT INTO public.unidad_funcional (
        id_instalacion_origen, id_instalacion_ultima_modificacion,
        op_id_alta, op_id_ultima_modificacion,
        id_inmueble, codigo_unidad, nombre_unidad, superficie,
        estado_administrativo, estado_operativo, fecha_alta, observaciones
    )
    VALUES
        (1, 1, v_op_id, v_op_id, v_inm_edificio, 'DEMO-UF-EDIF-1A', 'Departamento Demo 1A', 58.00, 'ACTIVA', 'DISPONIBLE', DATE '2026-01-01', 'DEMO UI unidad alquilada'),
        (1, 1, v_op_id, v_op_id, v_inm_edificio, 'DEMO-UF-EDIF-1B', 'Departamento Demo 1B', 62.00, 'ACTIVA', 'RESERVADA', DATE '2026-01-01', 'DEMO UI unidad ambigua'),
        (1, 1, v_op_id, v_op_id, v_inm_edificio, 'DEMO-UF-EDIF-2A', 'Departamento Demo 2A', 75.00, 'ACTIVA', 'DISPONIBLE', DATE '2026-01-01', 'DEMO UI unidad venta cuotas'),
        (1, 1, v_op_id, v_op_id, v_inm_casa, 'DEMO-UF-CASA-DEP', 'Deposito Demo Casa', 24.00, 'ACTIVA', 'USO_INTERNO', DATE '2026-01-01', 'DEMO UI unidad de servicio')
    ON CONFLICT (codigo_unidad) DO UPDATE SET
        id_inmueble = EXCLUDED.id_inmueble,
        nombre_unidad = EXCLUDED.nombre_unidad,
        superficie = EXCLUDED.superficie,
        estado_administrativo = EXCLUDED.estado_administrativo,
        estado_operativo = EXCLUDED.estado_operativo,
        observaciones = EXCLUDED.observaciones,
        op_id_ultima_modificacion = EXCLUDED.op_id_ultima_modificacion;

    SELECT id_unidad_funcional INTO v_uf_1a FROM public.unidad_funcional WHERE codigo_unidad = 'DEMO-UF-EDIF-1A';
    SELECT id_unidad_funcional INTO v_uf_1b FROM public.unidad_funcional WHERE codigo_unidad = 'DEMO-UF-EDIF-1B';
    SELECT id_unidad_funcional INTO v_uf_2a FROM public.unidad_funcional WHERE codigo_unidad = 'DEMO-UF-EDIF-2A';
    SELECT id_unidad_funcional INTO v_uf_deposito FROM public.unidad_funcional WHERE codigo_unidad = 'DEMO-UF-CASA-DEP';

    INSERT INTO public.servicio (
        id_instalacion_origen, id_instalacion_ultima_modificacion,
        op_id_alta, op_id_ultima_modificacion,
        codigo_servicio, nombre_servicio, descripcion, estado_servicio
    )
    VALUES
        (1, 1, v_op_id, v_op_id, 'DEMO-SRV-AGUA', 'Agua demo', 'Servicio de agua para UI demo', 'ACTIVO'),
        (1, 1, v_op_id, v_op_id, 'DEMO-SRV-LUZ', 'Luz demo', 'Servicio electrico para UI demo', 'ACTIVO'),
        (1, 1, v_op_id, v_op_id, 'DEMO-SRV-GAS', 'Gas demo', 'Servicio de gas para UI demo', 'ACTIVO'),
        (1, 1, v_op_id, v_op_id, 'DEMO-SRV-EXPENSAS', 'Expensas demo', 'Servicio comun/expensas para UI demo', 'ACTIVO')
    ON CONFLICT (codigo_servicio) DO UPDATE SET
        nombre_servicio = EXCLUDED.nombre_servicio,
        descripcion = EXCLUDED.descripcion,
        estado_servicio = EXCLUDED.estado_servicio,
        op_id_ultima_modificacion = EXCLUDED.op_id_ultima_modificacion;

    SELECT id_servicio INTO v_srv_agua FROM public.servicio WHERE codigo_servicio = 'DEMO-SRV-AGUA';
    SELECT id_servicio INTO v_srv_luz FROM public.servicio WHERE codigo_servicio = 'DEMO-SRV-LUZ';
    SELECT id_servicio INTO v_srv_gas FROM public.servicio WHERE codigo_servicio = 'DEMO-SRV-GAS';
    SELECT id_servicio INTO v_srv_expensas FROM public.servicio WHERE codigo_servicio = 'DEMO-SRV-EXPENSAS';

    INSERT INTO public.inmueble_servicio (
        id_instalacion_origen, id_instalacion_ultima_modificacion,
        op_id_alta, op_id_ultima_modificacion,
        id_inmueble, id_servicio, estado, fecha_alta, observaciones
    )
    SELECT 1, 1, v_op_id, v_op_id, x.id_inmueble, x.id_servicio, 'ACTIVO', DATE '2026-01-01', 'DEMO UI servicio inmueble'
    FROM (VALUES
        (v_inm_casa, v_srv_agua), (v_inm_casa, v_srv_luz), (v_inm_casa, v_srv_gas),
        (v_inm_edificio, v_srv_agua), (v_inm_edificio, v_srv_luz), (v_inm_edificio, v_srv_expensas),
        (v_inm_lote, v_srv_luz)
    ) AS x(id_inmueble, id_servicio)
    WHERE NOT EXISTS (
        SELECT 1 FROM public.inmueble_servicio s
        WHERE s.id_inmueble = x.id_inmueble
          AND s.id_servicio = x.id_servicio
          AND s.deleted_at IS NULL
    );

    INSERT INTO public.unidad_funcional_servicio (
        id_instalacion_origen, id_instalacion_ultima_modificacion,
        op_id_alta, op_id_ultima_modificacion,
        id_unidad_funcional, id_servicio, estado, fecha_alta, observaciones
    )
    SELECT 1, 1, v_op_id, v_op_id, x.id_unidad_funcional, x.id_servicio, 'ACTIVO', DATE '2026-01-01', 'DEMO UI servicio unidad'
    FROM (VALUES
        (v_uf_1a, v_srv_agua), (v_uf_1a, v_srv_luz), (v_uf_1a, v_srv_expensas),
        (v_uf_1b, v_srv_luz), (v_uf_1b, v_srv_expensas),
        (v_uf_2a, v_srv_agua), (v_uf_2a, v_srv_luz), (v_uf_2a, v_srv_gas),
        (v_uf_deposito, v_srv_luz)
    ) AS x(id_unidad_funcional, id_servicio)
    WHERE NOT EXISTS (
        SELECT 1 FROM public.unidad_funcional_servicio s
        WHERE s.id_unidad_funcional = x.id_unidad_funcional
          AND s.id_servicio = x.id_servicio
          AND s.deleted_at IS NULL
    );

    INSERT INTO public.asignacion_servicio_responsable (
        id_instalacion_origen, id_instalacion_ultima_modificacion,
        op_id_alta, op_id_ultima_modificacion,
        id_servicio, id_inmueble, id_unidad_funcional, id_persona,
        porcentaje_responsabilidad, fecha_desde, estado_asignacion, observaciones
    )
    SELECT 1, 1, v_op_id, v_op_id, x.id_servicio, x.id_inmueble, x.id_unidad_funcional,
           v_responsable_servicio, 100.00, DATE '2026-01-01', 'ACTIVA', 'DEMO UI responsable de servicio'
    FROM (VALUES
        (v_srv_agua, v_inm_casa, NULL::bigint),
        (v_srv_expensas, v_inm_edificio, NULL::bigint),
        (v_srv_luz, NULL::bigint, v_uf_1a),
        (v_srv_gas, NULL::bigint, v_uf_2a)
    ) AS x(id_servicio, id_inmueble, id_unidad_funcional)
    WHERE NOT EXISTS (
        SELECT 1 FROM public.asignacion_servicio_responsable a
        WHERE a.id_servicio = x.id_servicio
          AND COALESCE(a.id_inmueble, -1) = COALESCE(x.id_inmueble, -1)
          AND COALESCE(a.id_unidad_funcional, -1) = COALESCE(x.id_unidad_funcional, -1)
          AND a.id_persona = v_responsable_servicio
          AND a.deleted_at IS NULL
    );

    INSERT INTO public.disponibilidad (
        id_instalacion_origen, id_instalacion_ultima_modificacion,
        op_id_alta, op_id_ultima_modificacion,
        id_inmueble, id_unidad_funcional, estado_disponibilidad,
        fecha_desde, fecha_hasta, motivo, observaciones
    )
    SELECT 1, 1, v_op_id, v_op_id, x.id_inmueble, x.id_unidad_funcional,
           x.estado, x.fecha_desde, x.fecha_hasta, x.motivo, x.obs
    FROM (VALUES
        (v_inm_casa, NULL::bigint, 'DISPONIBLE', TIMESTAMP '2026-01-01 00:00:00', NULL::timestamp, 'demo', 'DEMO_UI:DISP-CASA-ACTUAL'),
        (v_inm_edificio, NULL::bigint, 'DISPONIBLE', TIMESTAMP '2026-01-01 00:00:00', NULL::timestamp, 'demo', 'DEMO_UI:DISP-EDIF-AMB-1'),
        (v_inm_edificio, NULL::bigint, 'RESERVADA', TIMESTAMP '2026-02-01 00:00:00', NULL::timestamp, 'demo', 'DEMO_UI:DISP-EDIF-AMB-2'),
        (v_inm_lote, NULL::bigint, 'DISPONIBLE', TIMESTAMP '2026-01-01 00:00:00', TIMESTAMP '2026-03-31 23:59:59', 'demo', 'DEMO_UI:DISP-LOTE-CERRADA'),
        (NULL::bigint, v_uf_1a, 'NO_DISPONIBLE', TIMESTAMP '2026-01-01 00:00:00', NULL::timestamp, 'demo', 'DEMO_UI:DISP-UF1A-ACTUAL'),
        (NULL::bigint, v_uf_1b, 'DISPONIBLE', TIMESTAMP '2026-01-01 00:00:00', NULL::timestamp, 'demo', 'DEMO_UI:DISP-UF1B-AMB-1'),
        (NULL::bigint, v_uf_1b, 'RESERVADA', TIMESTAMP '2026-02-01 00:00:00', NULL::timestamp, 'demo', 'DEMO_UI:DISP-UF1B-AMB-2'),
        (NULL::bigint, v_uf_2a, 'DISPONIBLE', TIMESTAMP '2026-01-01 00:00:00', NULL::timestamp, 'demo', 'DEMO_UI:DISP-UF2A-ACTUAL')
    ) AS x(id_inmueble, id_unidad_funcional, estado, fecha_desde, fecha_hasta, motivo, obs)
    WHERE NOT EXISTS (
        SELECT 1 FROM public.disponibilidad d
        WHERE d.observaciones = x.obs
          AND d.deleted_at IS NULL
    );

    INSERT INTO public.ocupacion (
        id_instalacion_origen, id_instalacion_ultima_modificacion,
        op_id_alta, op_id_ultima_modificacion,
        id_inmueble, id_unidad_funcional, tipo_ocupacion,
        fecha_desde, fecha_hasta, descripcion, observaciones
    )
    SELECT 1, 1, v_op_id, v_op_id, x.id_inmueble, x.id_unidad_funcional,
           x.tipo, x.fecha_desde, x.fecha_hasta, x.descripcion, x.obs
    FROM (VALUES
        (v_inm_casa, NULL::bigint, 'DESOCUPADO', TIMESTAMP '2026-01-01 00:00:00', NULL::timestamp, 'Sin ocupacion actual', 'DEMO_UI:OCUP-CASA-ACTUAL'),
        (v_inm_edificio, NULL::bigint, 'ADMINISTRACION', TIMESTAMP '2026-01-01 00:00:00', NULL::timestamp, 'Uso administrativo', 'DEMO_UI:OCUP-EDIF-AMB-1'),
        (v_inm_edificio, NULL::bigint, 'MIXTA', TIMESTAMP '2026-02-01 00:00:00', NULL::timestamp, 'Uso mixto', 'DEMO_UI:OCUP-EDIF-AMB-2'),
        (NULL::bigint, v_uf_1a, 'ALQUILER', TIMESTAMP '2026-01-01 00:00:00', NULL::timestamp, 'Contrato demo activo', 'DEMO_UI:OCUP-UF1A-ACTUAL'),
        (NULL::bigint, v_uf_1b, 'RESERVA', TIMESTAMP '2026-01-01 00:00:00', NULL::timestamp, 'Reserva demo', 'DEMO_UI:OCUP-UF1B-AMB-1'),
        (NULL::bigint, v_uf_1b, 'USO_INTERNO', TIMESTAMP '2026-02-01 00:00:00', NULL::timestamp, 'Uso interno demo', 'DEMO_UI:OCUP-UF1B-AMB-2')
    ) AS x(id_inmueble, id_unidad_funcional, tipo, fecha_desde, fecha_hasta, descripcion, obs)
    WHERE NOT EXISTS (
        SELECT 1 FROM public.ocupacion o
        WHERE o.observaciones = x.obs
          AND o.deleted_at IS NULL
    );

    INSERT INTO public.reserva_locativa (
        id_instalacion_origen, id_instalacion_ultima_modificacion,
        op_id_alta, op_id_ultima_modificacion,
        codigo_reserva, fecha_reserva, fecha_vencimiento, estado_reserva, observaciones
    )
    VALUES (
        1, 1, v_op_id, v_op_id,
        'DEMO-RES-LOC-001', TIMESTAMP '2025-12-15 10:00:00',
        TIMESTAMP '2026-01-15 10:00:00', 'confirmada', 'DEMO UI reserva locativa'
    )
    ON CONFLICT (codigo_reserva) DO UPDATE SET
        fecha_reserva = EXCLUDED.fecha_reserva,
        fecha_vencimiento = EXCLUDED.fecha_vencimiento,
        estado_reserva = EXCLUDED.estado_reserva,
        observaciones = EXCLUDED.observaciones,
        op_id_ultima_modificacion = EXCLUDED.op_id_ultima_modificacion;

    SELECT id_reserva_locativa INTO v_reserva_loc FROM public.reserva_locativa WHERE codigo_reserva = 'DEMO-RES-LOC-001';

    INSERT INTO public.reserva_locativa_objeto (
        id_instalacion_origen, id_instalacion_ultima_modificacion,
        op_id_alta, op_id_ultima_modificacion,
        id_reserva_locativa, id_inmueble, id_unidad_funcional, observaciones
    )
    SELECT 1, 1, v_op_id, v_op_id, v_reserva_loc, NULL::bigint, v_uf_1a, 'DEMO UI reserva locativa objeto'
    WHERE NOT EXISTS (
        SELECT 1 FROM public.reserva_locativa_objeto
        WHERE id_reserva_locativa = v_reserva_loc
          AND id_unidad_funcional = v_uf_1a
          AND deleted_at IS NULL
    );

    INSERT INTO public.contrato_alquiler (
        id_instalacion_origen, id_instalacion_ultima_modificacion,
        op_id_alta, op_id_ultima_modificacion,
        id_reserva_locativa, codigo_contrato, fecha_inicio, fecha_fin,
        estado_contrato, observaciones, dia_vencimiento_canon
    )
    VALUES (
        1, 1, v_op_id, v_op_id, v_reserva_loc,
        'DEMO-CA-001', DATE '2026-01-01', DATE '2026-12-31',
        'activo', 'DEMO UI contrato alquiler activo', 10
    )
    ON CONFLICT (codigo_contrato) DO UPDATE SET
        id_reserva_locativa = EXCLUDED.id_reserva_locativa,
        fecha_inicio = EXCLUDED.fecha_inicio,
        fecha_fin = EXCLUDED.fecha_fin,
        estado_contrato = EXCLUDED.estado_contrato,
        observaciones = EXCLUDED.observaciones,
        dia_vencimiento_canon = EXCLUDED.dia_vencimiento_canon,
        op_id_ultima_modificacion = EXCLUDED.op_id_ultima_modificacion;

    SELECT id_contrato_alquiler INTO v_contrato FROM public.contrato_alquiler WHERE codigo_contrato = 'DEMO-CA-001';

    INSERT INTO public.contrato_objeto_locativo (
        id_instalacion_origen, id_instalacion_ultima_modificacion,
        op_id_alta, op_id_ultima_modificacion,
        id_contrato_alquiler, id_inmueble, id_unidad_funcional, observaciones
    )
    SELECT 1, 1, v_op_id, v_op_id, v_contrato, NULL::bigint, v_uf_1a, 'DEMO UI objeto locativo'
    WHERE NOT EXISTS (
        SELECT 1 FROM public.contrato_objeto_locativo
        WHERE id_contrato_alquiler = v_contrato
          AND id_unidad_funcional = v_uf_1a
          AND deleted_at IS NULL
    );

    INSERT INTO public.condicion_economica_alquiler (
        id_instalacion_origen, id_instalacion_ultima_modificacion,
        op_id_alta, op_id_ultima_modificacion,
        id_contrato_alquiler, monto_base, periodicidad, moneda,
        fecha_desde, fecha_hasta, observaciones
    )
    SELECT 1, 1, v_op_id, v_op_id, v_contrato, 250000.00, 'MENSUAL', 'ARS',
           DATE '2026-01-01', DATE '2026-12-31', 'DEMO UI condicion economica alquiler'
    WHERE NOT EXISTS (
        SELECT 1 FROM public.condicion_economica_alquiler
        WHERE id_contrato_alquiler = v_contrato
          AND fecha_desde = DATE '2026-01-01'
          AND deleted_at IS NULL
    );

    INSERT INTO public.reserva_venta (
        id_instalacion_origen, id_instalacion_ultima_modificacion,
        op_id_alta, op_id_ultima_modificacion,
        codigo_reserva, fecha_reserva, estado_reserva, fecha_vencimiento, observaciones
    )
    VALUES
        (1, 1, v_op_id, v_op_id, 'DEMO-RES-VTA-CONTADO', TIMESTAMP '2026-01-10 10:00:00', 'confirmada', TIMESTAMP '2026-02-10 10:00:00', 'DEMO UI reserva venta contado'),
        (1, 1, v_op_id, v_op_id, 'DEMO-RES-VTA-ANTICIPO', TIMESTAMP '2026-02-10 10:00:00', 'confirmada', TIMESTAMP '2026-03-10 10:00:00', 'DEMO UI reserva venta anticipo y saldo'),
        (1, 1, v_op_id, v_op_id, 'DEMO-RES-VTA-CUOTAS', TIMESTAMP '2026-03-10 10:00:00', 'confirmada', TIMESTAMP '2026-04-10 10:00:00', 'DEMO UI reserva venta cuotas')
    ON CONFLICT (codigo_reserva) DO UPDATE SET
        fecha_reserva = EXCLUDED.fecha_reserva,
        estado_reserva = EXCLUDED.estado_reserva,
        fecha_vencimiento = EXCLUDED.fecha_vencimiento,
        observaciones = EXCLUDED.observaciones,
        op_id_ultima_modificacion = EXCLUDED.op_id_ultima_modificacion;

    SELECT id_reserva_venta INTO v_reserva_contado FROM public.reserva_venta WHERE codigo_reserva = 'DEMO-RES-VTA-CONTADO';
    SELECT id_reserva_venta INTO v_reserva_anticipo FROM public.reserva_venta WHERE codigo_reserva = 'DEMO-RES-VTA-ANTICIPO';
    SELECT id_reserva_venta INTO v_reserva_cuotas FROM public.reserva_venta WHERE codigo_reserva = 'DEMO-RES-VTA-CUOTAS';

    INSERT INTO public.reserva_venta_objeto_inmobiliario (
        id_instalacion_origen, id_instalacion_ultima_modificacion,
        op_id_alta, op_id_ultima_modificacion,
        id_reserva_venta, id_inmueble, id_unidad_funcional, observaciones
    )
    SELECT 1, 1, v_op_id, v_op_id, x.id_reserva_venta, x.id_inmueble, x.id_unidad_funcional, 'DEMO UI reserva venta objeto'
    FROM (VALUES
        (v_reserva_contado, v_inm_casa, NULL::bigint),
        (v_reserva_anticipo, v_inm_lote, NULL::bigint),
        (v_reserva_cuotas, NULL::bigint, v_uf_2a)
    ) AS x(id_reserva_venta, id_inmueble, id_unidad_funcional)
    WHERE NOT EXISTS (
        SELECT 1 FROM public.reserva_venta_objeto_inmobiliario rvo
        WHERE rvo.id_reserva_venta = x.id_reserva_venta
          AND COALESCE(rvo.id_inmueble, -1) = COALESCE(x.id_inmueble, -1)
          AND COALESCE(rvo.id_unidad_funcional, -1) = COALESCE(x.id_unidad_funcional, -1)
          AND rvo.deleted_at IS NULL
    );

    INSERT INTO public.venta (
        id_instalacion_origen, id_instalacion_ultima_modificacion,
        op_id_alta, op_id_ultima_modificacion,
        id_reserva_venta, codigo_venta, fecha_venta, estado_venta,
        monto_total, tipo_plan_financiero, moneda,
        importe_anticipo, fecha_vencimiento_anticipo,
        importe_saldo, fecha_vencimiento_saldo, observaciones
    )
    VALUES
        (1, 1, v_op_id, v_op_id, v_reserva_contado, 'DEMO-VTA-CONTADO', TIMESTAMP '2026-01-20 12:00:00', 'confirmada', 150000000.00, 'CONTADO', 'ARS', NULL, NULL, NULL, NULL, 'DEMO UI venta contado cancelada'),
        (1, 1, v_op_id, v_op_id, v_reserva_anticipo, 'DEMO-VTA-ANTICIPO', TIMESTAMP '2026-02-20 12:00:00', 'confirmada', 90000000.00, 'ANTICIPO_Y_SALDO', 'ARS', 30000000.00, DATE '2026-05-10', 60000000.00, DATE '2026-08-10', 'DEMO UI venta anticipo y saldo'),
        (1, 1, v_op_id, v_op_id, v_reserva_cuotas, 'DEMO-VTA-CUOTAS', TIMESTAMP '2026-03-20 12:00:00', 'confirmada', 120000000.00, 'CUOTAS_FIJAS', 'ARS', NULL, NULL, NULL, NULL, 'DEMO UI venta cuotas fijas')
    ON CONFLICT (codigo_venta) DO UPDATE SET
        id_reserva_venta = EXCLUDED.id_reserva_venta,
        fecha_venta = EXCLUDED.fecha_venta,
        estado_venta = EXCLUDED.estado_venta,
        monto_total = EXCLUDED.monto_total,
        tipo_plan_financiero = EXCLUDED.tipo_plan_financiero,
        moneda = EXCLUDED.moneda,
        importe_anticipo = EXCLUDED.importe_anticipo,
        fecha_vencimiento_anticipo = EXCLUDED.fecha_vencimiento_anticipo,
        importe_saldo = EXCLUDED.importe_saldo,
        fecha_vencimiento_saldo = EXCLUDED.fecha_vencimiento_saldo,
        observaciones = EXCLUDED.observaciones,
        op_id_ultima_modificacion = EXCLUDED.op_id_ultima_modificacion;

    SELECT id_venta INTO v_venta_contado FROM public.venta WHERE codigo_venta = 'DEMO-VTA-CONTADO';
    SELECT id_venta INTO v_venta_anticipo FROM public.venta WHERE codigo_venta = 'DEMO-VTA-ANTICIPO';
    SELECT id_venta INTO v_venta_cuotas FROM public.venta WHERE codigo_venta = 'DEMO-VTA-CUOTAS';

    INSERT INTO public.venta_objeto_inmobiliario (
        id_instalacion_origen, id_instalacion_ultima_modificacion,
        op_id_alta, op_id_ultima_modificacion,
        id_venta, id_inmueble, id_unidad_funcional, precio_asignado, observaciones
    )
    SELECT 1, 1, v_op_id, v_op_id, x.id_venta, x.id_inmueble, x.id_unidad_funcional, x.precio, 'DEMO UI venta objeto'
    FROM (VALUES
        (v_venta_contado, v_inm_casa, NULL::bigint, 150000000.00),
        (v_venta_anticipo, v_inm_lote, NULL::bigint, 90000000.00),
        (v_venta_cuotas, NULL::bigint, v_uf_2a, 120000000.00)
    ) AS x(id_venta, id_inmueble, id_unidad_funcional, precio)
    WHERE NOT EXISTS (
        SELECT 1 FROM public.venta_objeto_inmobiliario voi
        WHERE voi.id_venta = x.id_venta
          AND COALESCE(voi.id_inmueble, -1) = COALESCE(x.id_inmueble, -1)
          AND COALESCE(voi.id_unidad_funcional, -1) = COALESCE(x.id_unidad_funcional, -1)
          AND voi.deleted_at IS NULL
    );

    INSERT INTO public.venta_plan_cuota (
        id_instalacion_origen, id_instalacion_ultima_modificacion,
        op_id_alta, op_id_ultima_modificacion,
        id_venta, numero_cuota, importe_cuota, fecha_vencimiento, moneda, observaciones
    )
    SELECT 1, 1, v_op_id, v_op_id, v_venta_cuotas, x.numero_cuota, 40000000.00, x.fecha_vencimiento, 'ARS', 'DEMO UI cuota venta'
    FROM (VALUES
        (1, DATE '2026-06-10'),
        (2, DATE '2026-07-10'),
        (3, DATE '2026-08-10')
    ) AS x(numero_cuota, fecha_vencimiento)
    WHERE NOT EXISTS (
        SELECT 1 FROM public.venta_plan_cuota vpc
        WHERE vpc.id_venta = v_venta_cuotas
          AND vpc.numero_cuota = x.numero_cuota
          AND vpc.deleted_at IS NULL
    );

    INSERT INTO public.relacion_persona_rol (
        id_instalacion_origen, id_instalacion_ultima_modificacion,
        op_id_alta, op_id_ultima_modificacion,
        id_persona, id_rol_participacion, tipo_relacion, id_relacion,
        fecha_desde, observaciones
    )
    SELECT 1, 1, v_op_id, v_op_id, x.id_persona, x.id_rol, x.tipo_relacion,
           x.id_relacion, TIMESTAMP '2026-01-01 00:00:00', 'DEMO UI relacion persona rol'
    FROM (VALUES
        (v_locatario, v_rol_locatario, 'contrato_alquiler', v_contrato),
        (v_locador, v_rol_locador, 'contrato_alquiler', v_contrato),
        (v_garante, v_rol_garante, 'contrato_alquiler', v_contrato),
        (v_comprador, v_rol_comprador, 'venta', v_venta_contado),
        (v_persona_juridica, v_rol_comprador, 'venta', v_venta_anticipo),
        (v_comprador, v_rol_comprador, 'venta', v_venta_cuotas)
    ) AS x(id_persona, id_rol, tipo_relacion, id_relacion)
    WHERE NOT EXISTS (
        SELECT 1 FROM public.relacion_persona_rol rpr
        WHERE rpr.id_persona = x.id_persona
          AND rpr.id_rol_participacion = x.id_rol
          AND rpr.tipo_relacion = x.tipo_relacion
          AND rpr.id_relacion = x.id_relacion
          AND rpr.deleted_at IS NULL
    );

    INSERT INTO public.relacion_generadora (
        id_instalacion_origen, id_instalacion_ultima_modificacion,
        op_id_alta, op_id_ultima_modificacion,
        tipo_origen, id_origen, descripcion, fecha_alta, estado_relacion_generadora
    )
    SELECT 1, 1, v_op_id, v_op_id, x.tipo_origen, x.id_origen, x.descripcion,
           TIMESTAMP '2026-01-01 00:00:00', 'ACTIVA'
    FROM (VALUES
        ('contrato_alquiler', v_contrato, 'DEMO UI relacion financiera contrato alquiler'),
        ('venta', v_venta_contado, 'DEMO UI relacion financiera venta contado'),
        ('venta', v_venta_anticipo, 'DEMO UI relacion financiera venta anticipo saldo'),
        ('venta', v_venta_cuotas, 'DEMO UI relacion financiera venta cuotas')
    ) AS x(tipo_origen, id_origen, descripcion)
    WHERE NOT EXISTS (
        SELECT 1 FROM public.relacion_generadora rg
        WHERE rg.tipo_origen = x.tipo_origen
          AND rg.id_origen = x.id_origen
          AND rg.deleted_at IS NULL
    );

    INSERT INTO public.obligacion_financiera (
        id_instalacion_origen, id_instalacion_ultima_modificacion,
        op_id_alta, op_id_ultima_modificacion,
        id_relacion_generadora, codigo_obligacion_financiera,
        fecha_emision, fecha_vencimiento, estado_obligacion,
        moneda, importe_total, saldo_pendiente, importe_cancelado_acumulado,
        periodo_desde, periodo_hasta, observaciones
    )
    SELECT 1, 1, v_op_id, v_op_id, rg.id_relacion_generadora, x.codigo,
           x.fecha_emision, x.fecha_vencimiento, x.estado,
           'ARS', x.importe_total, x.saldo_pendiente, x.cancelado,
           x.periodo_desde, x.periodo_hasta, x.observaciones
    FROM (VALUES
        ('contrato_alquiler', v_contrato, 'DEMO-OBL-CA-ENE-2026', DATE '2026-01-01', DATE '2026-01-10', 'VENCIDA', 250000.00, 250000.00, 0.00, DATE '2026-01-01', DATE '2026-01-31', 'DEMO UI canon locativo vencido'),
        ('contrato_alquiler', v_contrato, 'DEMO-OBL-CA-JUN-2026', DATE '2026-06-01', DATE '2026-06-10', 'EMITIDA', 250000.00, 250000.00, 0.00, DATE '2026-06-01', DATE '2026-06-30', 'DEMO UI canon locativo pendiente'),
        ('venta', v_venta_contado, 'DEMO-OBL-VTA-CONTADO-CANCELADA', DATE '2026-01-20', DATE '2026-02-10', 'CANCELADA', 150000000.00, 0.00, 150000000.00, NULL::date, NULL::date, 'DEMO UI obligacion venta contado cancelada'),
        ('venta', v_venta_anticipo, 'DEMO-OBL-VTA-ANTICIPO', DATE '2026-02-20', DATE '2026-05-10', 'VENCIDA', 30000000.00, 30000000.00, 0.00, NULL::date, NULL::date, 'DEMO UI anticipo venta vencido'),
        ('venta', v_venta_anticipo, 'DEMO-OBL-VTA-SALDO', DATE '2026-02-20', DATE '2026-08-10', 'EMITIDA', 60000000.00, 60000000.00, 0.00, NULL::date, NULL::date, 'DEMO UI saldo venta pendiente'),
        ('venta', v_venta_cuotas, 'DEMO-OBL-VTA-CUOTA-1', DATE '2026-03-20', DATE '2026-06-10', 'EMITIDA', 40000000.00, 40000000.00, 0.00, DATE '2026-06-01', DATE '2026-06-30', 'DEMO UI cuota fija 1'),
        ('venta', v_venta_cuotas, 'DEMO-OBL-VTA-CUOTA-2', DATE '2026-03-20', DATE '2026-07-10', 'EMITIDA', 40000000.00, 40000000.00, 0.00, DATE '2026-07-01', DATE '2026-07-31', 'DEMO UI cuota fija 2'),
        ('venta', v_venta_cuotas, 'DEMO-OBL-VTA-CUOTA-3', DATE '2026-03-20', DATE '2026-08-10', 'EMITIDA', 40000000.00, 40000000.00, 0.00, DATE '2026-08-01', DATE '2026-08-31', 'DEMO UI cuota fija 3')
    ) AS x(tipo_origen, id_origen, codigo, fecha_emision, fecha_vencimiento, estado, importe_total, saldo_pendiente, cancelado, periodo_desde, periodo_hasta, observaciones)
    JOIN public.relacion_generadora rg
      ON rg.tipo_origen = x.tipo_origen
     AND rg.id_origen = x.id_origen
     AND rg.deleted_at IS NULL
    WHERE NOT EXISTS (
        SELECT 1 FROM public.obligacion_financiera ofi
        WHERE ofi.codigo_obligacion_financiera = x.codigo
          AND ofi.deleted_at IS NULL
    );

    INSERT INTO public.composicion_obligacion (
        id_instalacion_origen, id_instalacion_ultima_modificacion,
        op_id_alta, op_id_ultima_modificacion,
        id_obligacion_financiera, id_concepto_financiero,
        orden_composicion, estado_composicion_obligacion,
        importe_componente, saldo_componente, moneda_componente,
        detalle_calculo, observaciones
    )
    SELECT 1, 1, v_op_id, v_op_id, ofi.id_obligacion_financiera,
           cf.id_concepto_financiero, 1, 'ACTIVA',
           x.importe_componente, x.saldo_componente, 'ARS',
           '{"fuente":"seed_demo_ui"}', 'DEMO UI composicion obligacion'
    FROM (VALUES
        ('DEMO-OBL-CA-ENE-2026', 'CANON_LOCATIVO', 250000.00, 250000.00),
        ('DEMO-OBL-CA-JUN-2026', 'CANON_LOCATIVO', 250000.00, 250000.00),
        ('DEMO-OBL-VTA-CONTADO-CANCELADA', 'CAPITAL_VENTA', 150000000.00, 0.00),
        ('DEMO-OBL-VTA-ANTICIPO', 'ANTICIPO_VENTA', 30000000.00, 30000000.00),
        ('DEMO-OBL-VTA-SALDO', 'CAPITAL_VENTA', 60000000.00, 60000000.00),
        ('DEMO-OBL-VTA-CUOTA-1', 'CAPITAL_VENTA', 40000000.00, 40000000.00),
        ('DEMO-OBL-VTA-CUOTA-2', 'CAPITAL_VENTA', 40000000.00, 40000000.00),
        ('DEMO-OBL-VTA-CUOTA-3', 'CAPITAL_VENTA', 40000000.00, 40000000.00)
    ) AS x(codigo_obligacion, codigo_concepto, importe_componente, saldo_componente)
    JOIN public.obligacion_financiera ofi
      ON ofi.codigo_obligacion_financiera = x.codigo_obligacion
     AND ofi.deleted_at IS NULL
    JOIN public.concepto_financiero cf
      ON cf.codigo_concepto_financiero = x.codigo_concepto
     AND cf.deleted_at IS NULL
    WHERE NOT EXISTS (
        SELECT 1 FROM public.composicion_obligacion co
        WHERE co.id_obligacion_financiera = ofi.id_obligacion_financiera
          AND co.id_concepto_financiero = cf.id_concepto_financiero
          AND co.orden_composicion = 1
          AND co.deleted_at IS NULL
    );

    INSERT INTO public.obligacion_obligado (
        id_instalacion_origen, id_instalacion_ultima_modificacion,
        op_id_alta, op_id_ultima_modificacion,
        id_obligacion_financiera, id_persona, rol_obligado,
        porcentaje_responsabilidad, observaciones
    )
    SELECT 1, 1, v_op_id, v_op_id, ofi.id_obligacion_financiera,
           x.id_persona, x.rol_obligado, 100.00, 'DEMO UI obligado financiero'
    FROM (VALUES
        ('DEMO-OBL-CA-ENE-2026', v_locatario, 'LOCATARIO'),
        ('DEMO-OBL-CA-JUN-2026', v_locatario, 'LOCATARIO'),
        ('DEMO-OBL-VTA-CONTADO-CANCELADA', v_comprador, 'COMPRADOR'),
        ('DEMO-OBL-VTA-ANTICIPO', v_persona_juridica, 'COMPRADOR'),
        ('DEMO-OBL-VTA-SALDO', v_persona_juridica, 'COMPRADOR'),
        ('DEMO-OBL-VTA-CUOTA-1', v_comprador, 'COMPRADOR'),
        ('DEMO-OBL-VTA-CUOTA-2', v_comprador, 'COMPRADOR'),
        ('DEMO-OBL-VTA-CUOTA-3', v_comprador, 'COMPRADOR')
    ) AS x(codigo_obligacion, id_persona, rol_obligado)
    JOIN public.obligacion_financiera ofi
      ON ofi.codigo_obligacion_financiera = x.codigo_obligacion
     AND ofi.deleted_at IS NULL
    WHERE NOT EXISTS (
        SELECT 1 FROM public.obligacion_obligado oo
        WHERE oo.id_obligacion_financiera = ofi.id_obligacion_financiera
          AND oo.id_persona = x.id_persona
          AND oo.rol_obligado = x.rol_obligado
          AND oo.deleted_at IS NULL
    );

    INSERT INTO public.movimiento_financiero (
        id_instalacion_origen, id_instalacion_ultima_modificacion,
        op_id_alta, op_id_ultima_modificacion,
        uid_pago_grupo, codigo_pago_grupo, fecha_movimiento,
        tipo_movimiento, importe, signo, estado_movimiento, observaciones
    )
    SELECT 1, 1, v_op_id, v_op_id,
           '22222222-aaaa-bbbb-cccc-222222222222'::uuid,
           'DEMO-PAGO-CONTADO-001', TIMESTAMP '2026-02-10 12:00:00',
           'PAGO', 150000000.00, 'CREDITO', 'CONFIRMADO', 'DEMO UI pago scoped venta contado'
    WHERE NOT EXISTS (
        SELECT 1 FROM public.movimiento_financiero mf
        WHERE mf.codigo_pago_grupo = 'DEMO-PAGO-CONTADO-001'
          AND mf.deleted_at IS NULL
    );

    INSERT INTO public.aplicacion_financiera (
        id_instalacion_origen, id_instalacion_ultima_modificacion,
        op_id_alta, op_id_ultima_modificacion,
        id_movimiento_financiero, id_obligacion_financiera, id_composicion_obligacion,
        fecha_aplicacion, tipo_aplicacion, orden_aplicacion, importe_aplicado,
        origen_automatico_o_manual, observaciones
    )
    SELECT 1, 1, v_op_id, v_op_id,
           mf.id_movimiento_financiero, ofi.id_obligacion_financiera,
           co.id_composicion_obligacion, TIMESTAMP '2026-02-10 12:00:00',
           'PAGO', 1, 150000000.00, 'MANUAL', 'DEMO UI aplicacion pago contado'
    FROM public.movimiento_financiero mf
    JOIN public.obligacion_financiera ofi
      ON ofi.codigo_obligacion_financiera = 'DEMO-OBL-VTA-CONTADO-CANCELADA'
     AND ofi.deleted_at IS NULL
    JOIN public.composicion_obligacion co
      ON co.id_obligacion_financiera = ofi.id_obligacion_financiera
     AND co.deleted_at IS NULL
    WHERE mf.codigo_pago_grupo = 'DEMO-PAGO-CONTADO-001'
      AND mf.deleted_at IS NULL
      AND NOT EXISTS (
          SELECT 1 FROM public.aplicacion_financiera af
          WHERE af.id_movimiento_financiero = mf.id_movimiento_financiero
            AND af.id_obligacion_financiera = ofi.id_obligacion_financiera
            AND af.deleted_at IS NULL
      );

    UPDATE public.obligacion_financiera
       SET estado_obligacion = 'CANCELADA',
           saldo_pendiente = 0,
           importe_cancelado_acumulado = importe_total,
           op_id_ultima_modificacion = v_op_id
     WHERE codigo_obligacion_financiera = 'DEMO-OBL-VTA-CONTADO-CANCELADA'
       AND deleted_at IS NULL;
END $$;
