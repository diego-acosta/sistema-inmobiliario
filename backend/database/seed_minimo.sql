-- SEED MINIMO DEV
-- Requiere que reset_db aplique antes el baseline tecnico
-- con sucursal=1 e instalacion=1.
--
-- Objetivo:
-- 1. dejar un activo disponible para pruebas inmobiliarias basicas
-- 2. dejar datos minimos de persona/comercial para reservas y ventas
-- 3. dejar eventos outbox pendientes consistentes para publisher y consumer

DO $$
DECLARE
    v_op_id constant uuid := '11111111-1111-1111-1111-111111111111'::uuid;
    v_id_desarrollo bigint;
    v_id_inmueble_base bigint;
    v_id_unidad_base bigint;
    v_id_inmueble_confirm bigint;
    v_id_inmueble_escrituracion bigint;
    v_id_persona bigint;
    v_id_rol bigint;
    v_id_reserva_confirm bigint;
    v_id_reserva_escrituracion bigint;
    v_id_venta_confirm bigint;
    v_id_venta_escrituracion bigint;
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM public.sucursal
        WHERE id_sucursal = 1
          AND deleted_at IS NULL
    ) OR NOT EXISTS (
        SELECT 1
        FROM public.instalacion
        WHERE id_instalacion = 1
          AND deleted_at IS NULL
    ) THEN
        RAISE EXCEPTION
            'seed_minimo.sql requiere baseline tecnico previo con sucursal=1 e instalacion=1';
    END IF;

    INSERT INTO public.desarrollo (
        id_instalacion_origen,
        id_instalacion_ultima_modificacion,
        op_id_alta,
        op_id_ultima_modificacion,
        codigo_desarrollo,
        nombre_desarrollo,
        descripcion,
        estado_desarrollo,
        observaciones
    )
    VALUES (
        1,
        1,
        v_op_id,
        v_op_id,
        'DESA-SEED-001',
        'Desarrollo seed',
        'Desarrollo minimo para pruebas dev',
        'ACTIVO',
        'Seed minimo dev'
    )
    ON CONFLICT (codigo_desarrollo) DO NOTHING;

    SELECT id_desarrollo
    INTO v_id_desarrollo
    FROM public.desarrollo
    WHERE codigo_desarrollo = 'DESA-SEED-001';

    INSERT INTO public.persona (
        id_instalacion_origen,
        id_instalacion_ultima_modificacion,
        op_id_alta,
        op_id_ultima_modificacion,
        tipo_persona,
        codigo_persona,
        apellido,
        nombre,
        estado_persona,
        fecha_nacimiento_constitucion,
        observaciones
    )
    VALUES (
        1,
        1,
        v_op_id,
        v_op_id,
        'FISICA',
        'PER-SEED-001',
        'Seed',
        'Comprador',
        'ACTIVA',
        DATE '1990-01-01',
        'Persona minima para flujos comerciales'
    )
    ON CONFLICT (codigo_persona) DO NOTHING;

    SELECT id_persona
    INTO v_id_persona
    FROM public.persona
    WHERE codigo_persona = 'PER-SEED-001';

    IF NOT EXISTS (
        SELECT 1
        FROM public.cliente_comprador
        WHERE id_persona = v_id_persona
          AND deleted_at IS NULL
    ) THEN
        INSERT INTO public.cliente_comprador (
            id_instalacion_origen,
            id_instalacion_ultima_modificacion,
            op_id_alta,
            op_id_ultima_modificacion,
            id_persona,
            codigo_cliente_comprador,
            estado_cliente_comprador,
            observaciones
        )
        VALUES (
            1,
            1,
            v_op_id,
            v_op_id,
            v_id_persona,
            'CLI-COMP-SEED-001',
            'ACTIVO',
            'Compatibilidad comercial heredada del seed'
        );
    END IF;

    INSERT INTO public.rol_participacion (
        id_instalacion_origen,
        id_instalacion_ultima_modificacion,
        op_id_alta,
        op_id_ultima_modificacion,
        codigo_rol,
        nombre_rol,
        descripcion,
        estado_rol
    )
    VALUES (
        1,
        1,
        v_op_id,
        v_op_id,
        'ROL-COM-SEED-001',
        'Comprador comercial seed',
        'Rol de participacion minimo para reservas y ventas',
        'ACTIVO'
    )
    ON CONFLICT (codigo_rol) DO NOTHING;

    SELECT id_rol_participacion
    INTO v_id_rol
    FROM public.rol_participacion
    WHERE codigo_rol = 'ROL-COM-SEED-001';

    INSERT INTO public.inmueble (
        id_instalacion_origen,
        id_instalacion_ultima_modificacion,
        op_id_alta,
        op_id_ultima_modificacion,
        id_desarrollo,
        codigo_inmueble,
        nombre_inmueble,
        superficie,
        estado_administrativo,
        estado_juridico,
        observaciones
    )
    VALUES (
        1,
        1,
        v_op_id,
        v_op_id,
        v_id_desarrollo,
        'INM-SEED-001',
        'Inmueble base disponible',
        100.00,
        'ACTIVO',
        'REGULAR',
        'Activo base disponible para pruebas inmobiliarias'
    )
    ON CONFLICT (codigo_inmueble) DO NOTHING;

    SELECT id_inmueble
    INTO v_id_inmueble_base
    FROM public.inmueble
    WHERE codigo_inmueble = 'INM-SEED-001';

    INSERT INTO public.unidad_funcional (
        id_instalacion_origen,
        id_instalacion_ultima_modificacion,
        op_id_alta,
        op_id_ultima_modificacion,
        id_inmueble,
        codigo_unidad,
        nombre_unidad,
        superficie,
        estado_administrativo,
        estado_operativo,
        observaciones
    )
    VALUES (
        1,
        1,
        v_op_id,
        v_op_id,
        v_id_inmueble_base,
        'UF-SEED-001',
        'Unidad funcional base',
        50.00,
        'ACTIVA',
        'DISPONIBLE',
        'Unidad funcional minima del seed'
    )
    ON CONFLICT (codigo_unidad) DO NOTHING;

    SELECT id_unidad_funcional
    INTO v_id_unidad_base
    FROM public.unidad_funcional
    WHERE codigo_unidad = 'UF-SEED-001';

    IF NOT EXISTS (
        SELECT 1
        FROM public.disponibilidad
        WHERE id_inmueble = v_id_inmueble_base
          AND deleted_at IS NULL
    ) THEN
        INSERT INTO public.disponibilidad (
            id_instalacion_origen,
            id_instalacion_ultima_modificacion,
            op_id_alta,
            op_id_ultima_modificacion,
            id_inmueble,
            id_unidad_funcional,
            estado_disponibilidad,
            fecha_desde,
            fecha_hasta,
            motivo,
            observaciones
        )
        VALUES (
            1,
            1,
            v_op_id,
            v_op_id,
            v_id_inmueble_base,
            NULL,
            'DISPONIBLE',
            TIMESTAMP '2026-04-01 09:00:00',
            NULL,
            'seed_minimo',
            'Disponibilidad abierta base para pruebas'
        );
    END IF;

    INSERT INTO public.inmueble (
        id_instalacion_origen,
        id_instalacion_ultima_modificacion,
        op_id_alta,
        op_id_ultima_modificacion,
        id_desarrollo,
        codigo_inmueble,
        nombre_inmueble,
        superficie,
        estado_administrativo,
        estado_juridico,
        observaciones
    )
    VALUES (
        1,
        1,
        v_op_id,
        v_op_id,
        v_id_desarrollo,
        'INM-SEED-COM-001',
        'Inmueble seed venta confirmada',
        80.00,
        'ACTIVO',
        'REGULAR',
        'Activo reservado con evento venta_confirmada pendiente'
    )
    ON CONFLICT (codigo_inmueble) DO NOTHING;

    SELECT id_inmueble
    INTO v_id_inmueble_confirm
    FROM public.inmueble
    WHERE codigo_inmueble = 'INM-SEED-COM-001';

    IF NOT EXISTS (
        SELECT 1
        FROM public.disponibilidad
        WHERE id_inmueble = v_id_inmueble_confirm
          AND deleted_at IS NULL
    ) THEN
        INSERT INTO public.disponibilidad (
            id_instalacion_origen,
            id_instalacion_ultima_modificacion,
            op_id_alta,
            op_id_ultima_modificacion,
            id_inmueble,
            id_unidad_funcional,
            estado_disponibilidad,
            fecha_desde,
            fecha_hasta,
            motivo,
            observaciones
        )
        VALUES (
            1,
            1,
            v_op_id,
            v_op_id,
            v_id_inmueble_confirm,
            NULL,
            'DISPONIBLE',
            TIMESTAMP '2026-04-01 09:00:00',
            TIMESTAMP '2026-04-21 10:00:00',
            'seed_minimo',
            'Historial previo de activo comercial seed'
        );

        INSERT INTO public.disponibilidad (
            id_instalacion_origen,
            id_instalacion_ultima_modificacion,
            op_id_alta,
            op_id_ultima_modificacion,
            id_inmueble,
            id_unidad_funcional,
            estado_disponibilidad,
            fecha_desde,
            fecha_hasta,
            motivo,
            observaciones
        )
        VALUES (
            1,
            1,
            v_op_id,
            v_op_id,
            v_id_inmueble_confirm,
            NULL,
            'RESERVADA',
            TIMESTAMP '2026-04-21 10:00:00',
            NULL,
            'seed_minimo',
            'Estado vigente previo a publisher/consumer'
        );
    END IF;

    INSERT INTO public.reserva_venta (
        id_instalacion_origen,
        id_instalacion_ultima_modificacion,
        op_id_alta,
        op_id_ultima_modificacion,
        codigo_reserva,
        fecha_reserva,
        estado_reserva,
        fecha_vencimiento,
        observaciones
    )
    VALUES (
        1,
        1,
        v_op_id,
        v_op_id,
        'RV-SEED-001',
        TIMESTAMP '2026-04-21 10:00:00',
        'finalizada',
        TIMESTAMP '2026-04-30 10:00:00',
        'Reserva seed finalizada para venta confirmada'
    )
    ON CONFLICT (codigo_reserva) DO NOTHING;

    SELECT id_reserva_venta
    INTO v_id_reserva_confirm
    FROM public.reserva_venta
    WHERE codigo_reserva = 'RV-SEED-001';

    IF NOT EXISTS (
        SELECT 1
        FROM public.reserva_venta_objeto_inmobiliario
        WHERE id_reserva_venta = v_id_reserva_confirm
          AND id_inmueble = v_id_inmueble_confirm
          AND deleted_at IS NULL
    ) THEN
        INSERT INTO public.reserva_venta_objeto_inmobiliario (
            id_instalacion_origen,
            id_instalacion_ultima_modificacion,
            op_id_alta,
            op_id_ultima_modificacion,
            id_reserva_venta,
            id_inmueble,
            id_unidad_funcional,
            observaciones
        )
        VALUES (
            1,
            1,
            v_op_id,
            v_op_id,
            v_id_reserva_confirm,
            v_id_inmueble_confirm,
            NULL,
            'Objeto seed reserva comercial'
        );
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM public.relacion_persona_rol
        WHERE id_persona = v_id_persona
          AND id_rol_participacion = v_id_rol
          AND tipo_relacion = 'reserva_venta'
          AND id_relacion = v_id_reserva_confirm
          AND deleted_at IS NULL
    ) THEN
        INSERT INTO public.relacion_persona_rol (
            id_instalacion_origen,
            id_instalacion_ultima_modificacion,
            op_id_alta,
            op_id_ultima_modificacion,
            id_persona,
            id_rol_participacion,
            tipo_relacion,
            id_relacion,
            fecha_desde,
            fecha_hasta,
            observaciones
        )
        VALUES (
            1,
            1,
            v_op_id,
            v_op_id,
            v_id_persona,
            v_id_rol,
            'reserva_venta',
            v_id_reserva_confirm,
            TIMESTAMP '2026-04-21 10:00:00',
            NULL,
            'Participacion seed en reserva'
        );
    END IF;

    INSERT INTO public.venta (
        id_instalacion_origen,
        id_instalacion_ultima_modificacion,
        op_id_alta,
        op_id_ultima_modificacion,
        id_reserva_venta,
        codigo_venta,
        fecha_venta,
        estado_venta,
        monto_total,
        observaciones
    )
    VALUES (
        1,
        1,
        v_op_id,
        v_op_id,
        v_id_reserva_confirm,
        'V-SEED-001',
        TIMESTAMP '2026-04-22 11:00:00',
        'confirmada',
        100000.00,
        'Venta seed confirmada con outbox pendiente'
    )
    ON CONFLICT (codigo_venta) DO NOTHING;

    SELECT id_venta
    INTO v_id_venta_confirm
    FROM public.venta
    WHERE codigo_venta = 'V-SEED-001';

    IF NOT EXISTS (
        SELECT 1
        FROM public.venta_objeto_inmobiliario
        WHERE id_venta = v_id_venta_confirm
          AND id_inmueble = v_id_inmueble_confirm
          AND deleted_at IS NULL
    ) THEN
        INSERT INTO public.venta_objeto_inmobiliario (
            id_instalacion_origen,
            id_instalacion_ultima_modificacion,
            op_id_alta,
            op_id_ultima_modificacion,
            id_venta,
            id_inmueble,
            id_unidad_funcional,
            precio_asignado,
            observaciones
        )
        VALUES (
            1,
            1,
            v_op_id,
            v_op_id,
            v_id_venta_confirm,
            v_id_inmueble_confirm,
            NULL,
            100000.00,
            'Objeto seed venta confirmada'
        );
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM public.relacion_persona_rol
        WHERE id_persona = v_id_persona
          AND id_rol_participacion = v_id_rol
          AND tipo_relacion = 'venta'
          AND id_relacion = v_id_venta_confirm
          AND deleted_at IS NULL
    ) THEN
        INSERT INTO public.relacion_persona_rol (
            id_instalacion_origen,
            id_instalacion_ultima_modificacion,
            op_id_alta,
            op_id_ultima_modificacion,
            id_persona,
            id_rol_participacion,
            tipo_relacion,
            id_relacion,
            fecha_desde,
            fecha_hasta,
            observaciones
        )
        VALUES (
            1,
            1,
            v_op_id,
            v_op_id,
            v_id_persona,
            v_id_rol,
            'venta',
            v_id_venta_confirm,
            TIMESTAMP '2026-04-22 11:00:00',
            NULL,
            'Participacion seed en venta confirmada'
        );
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM public.outbox_event
        WHERE aggregate_type = 'venta'
          AND aggregate_id = v_id_venta_confirm
          AND event_type = 'venta_confirmada'
    ) THEN
        INSERT INTO public.outbox_event (
            event_type,
            aggregate_type,
            aggregate_id,
            payload,
            occurred_at,
            published_at,
            status,
            processing_reason,
            processing_metadata
        )
        VALUES (
            'venta_confirmada',
            'venta',
            v_id_venta_confirm,
            jsonb_build_object(
                'id_venta', v_id_venta_confirm,
                'id_reserva_venta', v_id_reserva_confirm,
                'estado_venta', 'confirmada',
                'objetos', jsonb_build_array(
                    jsonb_build_object(
                        'id_inmueble', v_id_inmueble_confirm,
                        'id_unidad_funcional', NULL
                    )
                )
            ),
            TIMESTAMP '2026-04-22 11:00:00',
            NULL,
            'PENDING',
            NULL,
            NULL
        );
    END IF;

    INSERT INTO public.inmueble (
        id_instalacion_origen,
        id_instalacion_ultima_modificacion,
        op_id_alta,
        op_id_ultima_modificacion,
        id_desarrollo,
        codigo_inmueble,
        nombre_inmueble,
        superficie,
        estado_administrativo,
        estado_juridico,
        observaciones
    )
    VALUES (
        1,
        1,
        v_op_id,
        v_op_id,
        v_id_desarrollo,
        'INM-SEED-ESC-001',
        'Inmueble seed escrituracion',
        90.00,
        'ACTIVO',
        'REGULAR',
        'Activo reservado con escrituracion pendiente de consumo'
    )
    ON CONFLICT (codigo_inmueble) DO NOTHING;

    SELECT id_inmueble
    INTO v_id_inmueble_escrituracion
    FROM public.inmueble
    WHERE codigo_inmueble = 'INM-SEED-ESC-001';

    IF NOT EXISTS (
        SELECT 1
        FROM public.disponibilidad
        WHERE id_inmueble = v_id_inmueble_escrituracion
          AND deleted_at IS NULL
    ) THEN
        INSERT INTO public.disponibilidad (
            id_instalacion_origen,
            id_instalacion_ultima_modificacion,
            op_id_alta,
            op_id_ultima_modificacion,
            id_inmueble,
            id_unidad_funcional,
            estado_disponibilidad,
            fecha_desde,
            fecha_hasta,
            motivo,
            observaciones
        )
        VALUES (
            1,
            1,
            v_op_id,
            v_op_id,
            v_id_inmueble_escrituracion,
            NULL,
            'DISPONIBLE',
            TIMESTAMP '2026-04-01 09:00:00',
            TIMESTAMP '2026-04-21 10:00:00',
            'seed_minimo',
            'Historial previo del activo escriturable seed'
        );

        INSERT INTO public.disponibilidad (
            id_instalacion_origen,
            id_instalacion_ultima_modificacion,
            op_id_alta,
            op_id_ultima_modificacion,
            id_inmueble,
            id_unidad_funcional,
            estado_disponibilidad,
            fecha_desde,
            fecha_hasta,
            motivo,
            observaciones
        )
        VALUES (
            1,
            1,
            v_op_id,
            v_op_id,
            v_id_inmueble_escrituracion,
            NULL,
            'RESERVADA',
            TIMESTAMP '2026-04-21 10:00:00',
            NULL,
            'seed_minimo',
            'Estado vigente previo al consumer de escrituracion'
        );
    END IF;

    INSERT INTO public.reserva_venta (
        id_instalacion_origen,
        id_instalacion_ultima_modificacion,
        op_id_alta,
        op_id_ultima_modificacion,
        codigo_reserva,
        fecha_reserva,
        estado_reserva,
        fecha_vencimiento,
        observaciones
    )
    VALUES (
        1,
        1,
        v_op_id,
        v_op_id,
        'RV-SEED-002',
        TIMESTAMP '2026-04-21 10:00:00',
        'finalizada',
        TIMESTAMP '2026-04-30 10:00:00',
        'Reserva seed para escrituracion'
    )
    ON CONFLICT (codigo_reserva) DO NOTHING;

    SELECT id_reserva_venta
    INTO v_id_reserva_escrituracion
    FROM public.reserva_venta
    WHERE codigo_reserva = 'RV-SEED-002';

    IF NOT EXISTS (
        SELECT 1
        FROM public.reserva_venta_objeto_inmobiliario
        WHERE id_reserva_venta = v_id_reserva_escrituracion
          AND id_inmueble = v_id_inmueble_escrituracion
          AND deleted_at IS NULL
    ) THEN
        INSERT INTO public.reserva_venta_objeto_inmobiliario (
            id_instalacion_origen,
            id_instalacion_ultima_modificacion,
            op_id_alta,
            op_id_ultima_modificacion,
            id_reserva_venta,
            id_inmueble,
            id_unidad_funcional,
            observaciones
        )
        VALUES (
            1,
            1,
            v_op_id,
            v_op_id,
            v_id_reserva_escrituracion,
            v_id_inmueble_escrituracion,
            NULL,
            'Objeto seed reserva escriturable'
        );
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM public.relacion_persona_rol
        WHERE id_persona = v_id_persona
          AND id_rol_participacion = v_id_rol
          AND tipo_relacion = 'reserva_venta'
          AND id_relacion = v_id_reserva_escrituracion
          AND deleted_at IS NULL
    ) THEN
        INSERT INTO public.relacion_persona_rol (
            id_instalacion_origen,
            id_instalacion_ultima_modificacion,
            op_id_alta,
            op_id_ultima_modificacion,
            id_persona,
            id_rol_participacion,
            tipo_relacion,
            id_relacion,
            fecha_desde,
            fecha_hasta,
            observaciones
        )
        VALUES (
            1,
            1,
            v_op_id,
            v_op_id,
            v_id_persona,
            v_id_rol,
            'reserva_venta',
            v_id_reserva_escrituracion,
            TIMESTAMP '2026-04-21 10:00:00',
            NULL,
            'Participacion seed en reserva escriturable'
        );
    END IF;

    INSERT INTO public.venta (
        id_instalacion_origen,
        id_instalacion_ultima_modificacion,
        op_id_alta,
        op_id_ultima_modificacion,
        id_reserva_venta,
        codigo_venta,
        fecha_venta,
        estado_venta,
        monto_total,
        observaciones
    )
    VALUES (
        1,
        1,
        v_op_id,
        v_op_id,
        v_id_reserva_escrituracion,
        'V-SEED-002',
        TIMESTAMP '2026-04-22 12:00:00',
        'confirmada',
        125000.00,
        'Venta seed confirmada con escrituracion pendiente'
    )
    ON CONFLICT (codigo_venta) DO NOTHING;

    SELECT id_venta
    INTO v_id_venta_escrituracion
    FROM public.venta
    WHERE codigo_venta = 'V-SEED-002';

    IF NOT EXISTS (
        SELECT 1
        FROM public.venta_objeto_inmobiliario
        WHERE id_venta = v_id_venta_escrituracion
          AND id_inmueble = v_id_inmueble_escrituracion
          AND deleted_at IS NULL
    ) THEN
        INSERT INTO public.venta_objeto_inmobiliario (
            id_instalacion_origen,
            id_instalacion_ultima_modificacion,
            op_id_alta,
            op_id_ultima_modificacion,
            id_venta,
            id_inmueble,
            id_unidad_funcional,
            precio_asignado,
            observaciones
        )
        VALUES (
            1,
            1,
            v_op_id,
            v_op_id,
            v_id_venta_escrituracion,
            v_id_inmueble_escrituracion,
            NULL,
            125000.00,
            'Objeto seed venta escriturada'
        );
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM public.relacion_persona_rol
        WHERE id_persona = v_id_persona
          AND id_rol_participacion = v_id_rol
          AND tipo_relacion = 'venta'
          AND id_relacion = v_id_venta_escrituracion
          AND deleted_at IS NULL
    ) THEN
        INSERT INTO public.relacion_persona_rol (
            id_instalacion_origen,
            id_instalacion_ultima_modificacion,
            op_id_alta,
            op_id_ultima_modificacion,
            id_persona,
            id_rol_participacion,
            tipo_relacion,
            id_relacion,
            fecha_desde,
            fecha_hasta,
            observaciones
        )
        VALUES (
            1,
            1,
            v_op_id,
            v_op_id,
            v_id_persona,
            v_id_rol,
            'venta',
            v_id_venta_escrituracion,
            TIMESTAMP '2026-04-22 12:00:00',
            NULL,
            'Participacion seed en venta escriturada'
        );
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM public.escrituracion
        WHERE id_venta = v_id_venta_escrituracion
          AND deleted_at IS NULL
    ) THEN
        INSERT INTO public.escrituracion (
            id_instalacion_origen,
            id_instalacion_ultima_modificacion,
            op_id_alta,
            op_id_ultima_modificacion,
            id_venta,
            fecha_escrituracion,
            numero_escritura,
            observaciones
        )
        VALUES (
            1,
            1,
            v_op_id,
            v_op_id,
            v_id_venta_escrituracion,
            TIMESTAMP '2026-04-24 11:00:00',
            'ESC-SEED-001',
            'Escrituracion seed pendiente de consumo inmobiliario'
        );
    END IF;

    IF NOT EXISTS (
        SELECT 1
        FROM public.outbox_event
        WHERE aggregate_type = 'venta'
          AND aggregate_id = v_id_venta_escrituracion
          AND event_type = 'escrituracion_registrada'
    ) THEN
        INSERT INTO public.outbox_event (
            event_type,
            aggregate_type,
            aggregate_id,
            payload,
            occurred_at,
            published_at,
            status,
            processing_reason,
            processing_metadata
        )
        VALUES (
            'escrituracion_registrada',
            'venta',
            v_id_venta_escrituracion,
            jsonb_build_object(
                'id_venta', v_id_venta_escrituracion,
                'fecha_escrituracion', '2026-04-24T11:00:00',
                'numero_escritura', 'ESC-SEED-001',
                'objetos', jsonb_build_array(
                    jsonb_build_object(
                        'id_inmueble', v_id_inmueble_escrituracion,
                        'id_unidad_funcional', NULL
                    )
                )
            ),
            TIMESTAMP '2026-04-24 11:00:00',
            NULL,
            'PENDING',
            NULL,
            NULL
        );
    END IF;
END
$$;
