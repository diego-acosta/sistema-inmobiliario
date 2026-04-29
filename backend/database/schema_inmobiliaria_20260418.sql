--
-- PostgreSQL database dump
--

\restrict SvGuuWBELfRzzBtgZiWG8D2cOqEd41CZoOjTpudlYg4WzHEUe94dZUATbwf7HZA

-- Dumped from database version 18.3
-- Dumped by pg_dump version 18.3

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: pgcrypto; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pgcrypto WITH SCHEMA public;


--
-- Name: EXTENSION pgcrypto; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION pgcrypto IS 'cryptographic functions';


--
-- Name: fn_assert_instalacion_pertenece_a_sucursal(bigint, bigint, text); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.fn_assert_instalacion_pertenece_a_sucursal(p_id_instalacion bigint, p_id_sucursal bigint, p_contexto text) RETURNS void
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_ok BOOLEAN;
BEGIN
    IF p_id_instalacion IS NULL OR p_id_sucursal IS NULL THEN
        RETURN;
    END IF;

    SELECT EXISTS (
        SELECT 1
        FROM instalacion i
        WHERE i.id_instalacion = p_id_instalacion
          AND i.id_sucursal = p_id_sucursal
    ) INTO v_ok;

    IF NOT v_ok THEN
        RAISE EXCEPTION 'Inconsistencia sucursal/instalacion en %: instalacion % no pertenece a sucursal %',
            p_contexto, p_id_instalacion, p_id_sucursal;
    END IF;
END;
$$;


--
-- Name: fn_ranges_overlap(timestamp without time zone, timestamp without time zone, timestamp without time zone, timestamp without time zone); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.fn_ranges_overlap(p_desde_1 timestamp without time zone, p_hasta_1 timestamp without time zone, p_desde_2 timestamp without time zone, p_hasta_2 timestamp without time zone) RETURNS boolean
    LANGUAGE sql IMMUTABLE
    AS $$
    SELECT tsrange(p_desde_1, COALESCE(p_hasta_1, 'infinity'::timestamp), '[]')
        && tsrange(p_desde_2, COALESCE(p_hasta_2, 'infinity'::timestamp), '[]');
$$;


--
-- Name: fn_ranges_overlap_date(date, date, date, date); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.fn_ranges_overlap_date(p_desde_1 date, p_hasta_1 date, p_desde_2 date, p_hasta_2 date) RETURNS boolean
    LANGUAGE sql IMMUTABLE
    AS $$
    SELECT daterange(p_desde_1, COALESCE(p_hasta_1, 'infinity'::date), '[]')
        && daterange(p_desde_2, COALESCE(p_hasta_2, 'infinity'::date), '[]');
$$;


--
-- Name: trg_aplicacion_financiera_refrescar_saldo_obligacion(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.trg_aplicacion_financiera_refrescar_saldo_obligacion() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
DECLARE
BEGIN
    IF TG_OP IN ('UPDATE', 'DELETE') THEN
        IF OLD.id_composicion_obligacion IS NOT NULL THEN
            UPDATE composicion_obligacion c
               SET saldo_componente = GREATEST(
                    0,
                    c.importe_componente - COALESCE((
                        SELECT SUM(a.importe_aplicado)
                        FROM aplicacion_financiera a
                        WHERE a.id_composicion_obligacion = c.id_composicion_obligacion
                    ), 0)
               ),
                   updated_at = CURRENT_TIMESTAMP,
                   version_registro = c.version_registro + 1
             WHERE c.id_composicion_obligacion = OLD.id_composicion_obligacion;
        END IF;

        UPDATE obligacion_financiera o
           SET saldo_pendiente = GREATEST(
                0,
                o.importe_total - COALESCE((
                    SELECT SUM(a.importe_aplicado)
                    FROM aplicacion_financiera a
                    WHERE a.id_obligacion_financiera = o.id_obligacion_financiera
                ), 0)
           ),
               importe_cancelado_acumulado = COALESCE((
                    SELECT SUM(a.importe_aplicado)
                    FROM aplicacion_financiera a
                    WHERE a.id_obligacion_financiera = o.id_obligacion_financiera
                ), 0),
               updated_at = CURRENT_TIMESTAMP,
               version_registro = o.version_registro + 1
         WHERE o.id_obligacion_financiera = OLD.id_obligacion_financiera;
    END IF;

    IF TG_OP IN ('INSERT', 'UPDATE') THEN
        IF NEW.id_composicion_obligacion IS NOT NULL THEN
            UPDATE composicion_obligacion c
               SET saldo_componente = GREATEST(
                    0,
                    c.importe_componente - COALESCE((
                        SELECT SUM(a.importe_aplicado)
                        FROM aplicacion_financiera a
                        WHERE a.id_composicion_obligacion = c.id_composicion_obligacion
                    ), 0)
               ),
                   updated_at = CURRENT_TIMESTAMP,
                   version_registro = c.version_registro + 1
             WHERE c.id_composicion_obligacion = NEW.id_composicion_obligacion;
        END IF;

        UPDATE obligacion_financiera o
           SET saldo_pendiente = GREATEST(
                0,
                o.importe_total - COALESCE((
                    SELECT SUM(a.importe_aplicado)
                    FROM aplicacion_financiera a
                    WHERE a.id_obligacion_financiera = o.id_obligacion_financiera
                ), 0)
           ),
               importe_cancelado_acumulado = COALESCE((
                    SELECT SUM(a.importe_aplicado)
                    FROM aplicacion_financiera a
                    WHERE a.id_obligacion_financiera = o.id_obligacion_financiera
                ), 0),
               updated_at = CURRENT_TIMESTAMP,
               version_registro = o.version_registro + 1
         WHERE o.id_obligacion_financiera = NEW.id_obligacion_financiera;
    END IF;

    RETURN COALESCE(NEW, OLD);
END;
$$;


--
-- Name: trg_aplicacion_financiera_validar_consistencia(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.trg_aplicacion_financiera_validar_consistencia() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_id_obligacion_composicion BIGINT;
    v_importe_total_obligacion NUMERIC(18,2);
    v_importe_total_composicion NUMERIC(18,2);
    v_aplicado_obligacion NUMERIC(18,2);
    v_aplicado_composicion NUMERIC(18,2);
BEGIN
    IF NEW.id_composicion_obligacion IS NOT NULL THEN
        SELECT c.id_obligacion_financiera, c.importe_componente
          INTO v_id_obligacion_composicion, v_importe_total_composicion
          FROM composicion_obligacion c
         WHERE c.id_composicion_obligacion = NEW.id_composicion_obligacion;

        IF v_id_obligacion_composicion IS NULL THEN
            RAISE EXCEPTION 'Composicion inexistente en aplicacion_financiera: %', NEW.id_composicion_obligacion;
        END IF;

        IF v_id_obligacion_composicion <> NEW.id_obligacion_financiera THEN
            RAISE EXCEPTION 'La composicion % no pertenece a la obligacion %',
                NEW.id_composicion_obligacion, NEW.id_obligacion_financiera;
        END IF;

        SELECT COALESCE(SUM(a.importe_aplicado), 0)
          INTO v_aplicado_composicion
          FROM aplicacion_financiera a
         WHERE a.id_composicion_obligacion = NEW.id_composicion_obligacion
           AND (TG_OP <> 'UPDATE' OR a.id_aplicacion_financiera <> OLD.id_aplicacion_financiera);

        IF v_aplicado_composicion + NEW.importe_aplicado > v_importe_total_composicion THEN
            RAISE EXCEPTION 'Sobreaplicacion de composicion: importe % excede disponible % en composicion %',
                NEW.importe_aplicado,
                v_importe_total_composicion - v_aplicado_composicion,
                NEW.id_composicion_obligacion;
        END IF;
    END IF;

    SELECT o.importe_total
      INTO v_importe_total_obligacion
      FROM obligacion_financiera o
     WHERE o.id_obligacion_financiera = NEW.id_obligacion_financiera;

    IF v_importe_total_obligacion IS NULL THEN
        RAISE EXCEPTION 'Obligacion inexistente en aplicacion_financiera: %', NEW.id_obligacion_financiera;
    END IF;

    SELECT COALESCE(SUM(a.importe_aplicado), 0)
      INTO v_aplicado_obligacion
      FROM aplicacion_financiera a
     WHERE a.id_obligacion_financiera = NEW.id_obligacion_financiera
       AND (TG_OP <> 'UPDATE' OR a.id_aplicacion_financiera <> OLD.id_aplicacion_financiera);

    IF v_aplicado_obligacion + NEW.importe_aplicado > v_importe_total_obligacion THEN
        RAISE EXCEPTION 'Sobreaplicacion de obligacion: importe % excede disponible % en obligacion %',
            NEW.importe_aplicado,
            v_importe_total_obligacion - v_aplicado_obligacion,
            NEW.id_obligacion_financiera;
    END IF;

    RETURN NEW;
END;
$$;


--
-- Name: trg_condicion_economica_alquiler_no_solapada(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.trg_condicion_economica_alquiler_no_solapada() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM condicion_economica_alquiler x
        WHERE x.id_condicion_economica <> COALESCE(NEW.id_condicion_economica, -1)
          AND x.id_contrato_alquiler = NEW.id_contrato_alquiler
          AND COALESCE(x.moneda, '') = COALESCE(NEW.moneda, '')
          AND x.deleted_at IS NULL
          AND fn_ranges_overlap_date(x.fecha_desde, x.fecha_hasta, NEW.fecha_desde, NEW.fecha_hasta)
    ) THEN
        RAISE EXCEPTION 'Solapamiento de vigencia en condicion_economica_alquiler para contrato %, moneda %',
            NEW.id_contrato_alquiler, NEW.moneda;
    END IF;

    RETURN NEW;
END;
$$;


--
-- Name: trg_core_ef_sync_defaults_insert(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.trg_core_ef_sync_defaults_insert() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    IF NEW.uid_global IS NULL THEN
        NEW.uid_global := gen_random_uuid();
    END IF;

    IF NEW.version_registro IS NULL OR NEW.version_registro < 1 THEN
        NEW.version_registro := 1;
    END IF;

    IF NEW.created_at IS NULL THEN
        NEW.created_at := CURRENT_TIMESTAMP;
    END IF;

    IF NEW.updated_at IS NULL THEN
        NEW.updated_at := NEW.created_at;
    END IF;

    IF NEW.id_instalacion_ultima_modificacion IS NULL THEN
        NEW.id_instalacion_ultima_modificacion := NEW.id_instalacion_origen;
    END IF;

    IF NEW.op_id_ultima_modificacion IS NULL THEN
        NEW.op_id_ultima_modificacion := NEW.op_id_alta;
    END IF;

    RETURN NEW;
END;
$$;


--
-- Name: trg_core_ef_sync_defaults_update(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.trg_core_ef_sync_defaults_update() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.uid_global := OLD.uid_global;
    NEW.created_at := OLD.created_at;
    NEW.id_instalacion_origen := OLD.id_instalacion_origen;
    NEW.op_id_alta := OLD.op_id_alta;

    IF NEW.updated_at IS NULL OR NEW.updated_at = OLD.updated_at THEN
        NEW.updated_at := CURRENT_TIMESTAMP;
    END IF;

    IF NEW.id_instalacion_ultima_modificacion IS NULL THEN
        NEW.id_instalacion_ultima_modificacion := OLD.id_instalacion_ultima_modificacion;
    END IF;

    IF NEW.op_id_ultima_modificacion IS NULL THEN
        NEW.op_id_ultima_modificacion := OLD.op_id_ultima_modificacion;
    END IF;

    IF ROW(
        NEW.deleted_at,
        NEW.id_instalacion_ultima_modificacion,
        NEW.op_id_ultima_modificacion,
        NEW.updated_at,
        NEW.version_registro
    ) IS DISTINCT FROM ROW(
        OLD.deleted_at,
        OLD.id_instalacion_ultima_modificacion,
        OLD.op_id_ultima_modificacion,
        OLD.updated_at,
        OLD.version_registro
    )
    OR ROW(NEW.*) IS DISTINCT FROM ROW(OLD.*) THEN
        NEW.version_registro := COALESCE(OLD.version_registro, 0) + 1;
    ELSE
        NEW.version_registro := OLD.version_registro;
    END IF;

    RETURN NEW;
END;
$$;


--
-- Name: trg_factura_servicio_validar_asociacion(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.trg_factura_servicio_validar_asociacion() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    IF NOT (
        (NEW.id_inmueble IS NOT NULL AND NEW.id_unidad_funcional IS NULL)
        OR
        (NEW.id_inmueble IS NULL AND NEW.id_unidad_funcional IS NOT NULL)
    ) THEN
        RAISE EXCEPTION 'Debe especificarse exactamente uno: id_inmueble o id_unidad_funcional';
    END IF;

    IF NEW.id_inmueble IS NOT NULL THEN
        IF NOT EXISTS (
            SELECT 1
            FROM public.inmueble_servicio isv
            WHERE isv.id_inmueble = NEW.id_inmueble
              AND isv.id_servicio = NEW.id_servicio
              AND isv.deleted_at IS NULL
        ) THEN
            RAISE EXCEPTION 'No existe asociacion activa entre inmueble % y servicio %', NEW.id_inmueble, NEW.id_servicio;
        END IF;
    END IF;

    IF NEW.id_unidad_funcional IS NOT NULL THEN
        IF NOT EXISTS (
            SELECT 1
            FROM public.unidad_funcional_servicio ufs
            WHERE ufs.id_unidad_funcional = NEW.id_unidad_funcional
              AND ufs.id_servicio = NEW.id_servicio
              AND ufs.deleted_at IS NULL
        ) THEN
            RAISE EXCEPTION 'No existe asociacion activa entre unidad funcional % y servicio %', NEW.id_unidad_funcional, NEW.id_servicio;
        END IF;
    END IF;

    RETURN NEW;
END;
$$;


--
-- Name: trg_desarrollo_sucursal_no_solapada(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.trg_desarrollo_sucursal_no_solapada() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM desarrollo_sucursal x
        WHERE x.id_desarrollo_sucursal <> COALESCE(NEW.id_desarrollo_sucursal, -1)
          AND x.id_desarrollo = NEW.id_desarrollo
          AND x.id_sucursal = NEW.id_sucursal
          AND x.deleted_at IS NULL
          AND fn_ranges_overlap(x.fecha_desde, x.fecha_hasta, NEW.fecha_desde, NEW.fecha_hasta)
    ) THEN
        RAISE EXCEPTION 'Solapamiento de vigencia en desarrollo_sucursal para desarrollo %, sucursal %',
            NEW.id_desarrollo, NEW.id_sucursal;
    END IF;

    RETURN NEW;
END;
$$;


--
-- Name: trg_disponibilidad_no_solapada(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.trg_disponibilidad_no_solapada() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM disponibilidad x
        WHERE x.id_disponibilidad <> COALESCE(NEW.id_disponibilidad, -1)
          AND COALESCE(x.id_inmueble, -1) = COALESCE(NEW.id_inmueble, -1)
          AND COALESCE(x.id_unidad_funcional, -1) = COALESCE(NEW.id_unidad_funcional, -1)
          AND x.estado_disponibilidad = NEW.estado_disponibilidad
          AND x.deleted_at IS NULL
          AND fn_ranges_overlap(x.fecha_desde, x.fecha_hasta, NEW.fecha_desde, NEW.fecha_hasta)
    ) THEN
        RAISE EXCEPTION 'Solapamiento de vigencia en disponibilidad para inmueble %, unidad_funcional %, estado %',
            NEW.id_inmueble, NEW.id_unidad_funcional, NEW.estado_disponibilidad;
    END IF;

    RETURN NEW;
END;
$$;


--
-- Name: trg_documento_entidad_polimorfica(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.trg_documento_entidad_polimorfica() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    IF NEW.tipo_entidad NOT IN (
        'persona',
        'venta',
        'contrato_alquiler',
        'cesion',
        'escrituracion',
        'obligacion_financiera',
        'movimiento_financiero'
    ) THEN
        RAISE EXCEPTION 'tipo_entidad no permitido en documento_entidad: %', NEW.tipo_entidad;
    END IF;

    CASE NEW.tipo_entidad
        WHEN 'persona' THEN
            IF NOT EXISTS (SELECT 1 FROM persona WHERE id_persona = NEW.id_entidad) THEN
                RAISE EXCEPTION 'documento_entidad referencia persona inexistente: %', NEW.id_entidad;
            END IF;
        WHEN 'venta' THEN
            IF NOT EXISTS (SELECT 1 FROM venta WHERE id_venta = NEW.id_entidad) THEN
                RAISE EXCEPTION 'documento_entidad referencia venta inexistente: %', NEW.id_entidad;
            END IF;
        WHEN 'contrato_alquiler' THEN
            IF NOT EXISTS (SELECT 1 FROM contrato_alquiler WHERE id_contrato_alquiler = NEW.id_entidad) THEN
                RAISE EXCEPTION 'documento_entidad referencia contrato_alquiler inexistente: %', NEW.id_entidad;
            END IF;
        WHEN 'cesion' THEN
            IF NOT EXISTS (SELECT 1 FROM cesion WHERE id_cesion = NEW.id_entidad) THEN
                RAISE EXCEPTION 'documento_entidad referencia cesion inexistente: %', NEW.id_entidad;
            END IF;
        WHEN 'escrituracion' THEN
            IF NOT EXISTS (SELECT 1 FROM escrituracion WHERE id_escrituracion = NEW.id_entidad) THEN
                RAISE EXCEPTION 'documento_entidad referencia escrituracion inexistente: %', NEW.id_entidad;
            END IF;
        WHEN 'obligacion_financiera' THEN
            IF NOT EXISTS (SELECT 1 FROM obligacion_financiera WHERE id_obligacion_financiera = NEW.id_entidad) THEN
                RAISE EXCEPTION 'documento_entidad referencia obligacion_financiera inexistente: %', NEW.id_entidad;
            END IF;
        WHEN 'movimiento_financiero' THEN
            IF NOT EXISTS (SELECT 1 FROM movimiento_financiero WHERE id_movimiento_financiero = NEW.id_entidad) THEN
                RAISE EXCEPTION 'documento_entidad referencia movimiento_financiero inexistente: %', NEW.id_entidad;
            END IF;
    END CASE;

    RETURN NEW;
END;
$$;


--
-- Name: trg_emision_numeracion_polimorfica(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.trg_emision_numeracion_polimorfica() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    IF NEW.tipo_entidad NOT IN (
        'documento_logico',
        'documento_version',
        'contrato_alquiler',
        'instrumento_compraventa',
        'movimiento_financiero'
    ) THEN
        RAISE EXCEPTION 'tipo_entidad no permitido en emision_numeracion: %', NEW.tipo_entidad;
    END IF;

    CASE NEW.tipo_entidad
        WHEN 'documento_logico' THEN
            IF NOT EXISTS (SELECT 1 FROM documento_logico WHERE id_documento_logico = NEW.id_entidad) THEN
                RAISE EXCEPTION 'emision_numeracion referencia documento_logico inexistente: %', NEW.id_entidad;
            END IF;
        WHEN 'documento_version' THEN
            IF NOT EXISTS (SELECT 1 FROM documento_version WHERE id_documento_version = NEW.id_entidad) THEN
                RAISE EXCEPTION 'emision_numeracion referencia documento_version inexistente: %', NEW.id_entidad;
            END IF;
        WHEN 'contrato_alquiler' THEN
            IF NOT EXISTS (SELECT 1 FROM contrato_alquiler WHERE id_contrato_alquiler = NEW.id_entidad) THEN
                RAISE EXCEPTION 'emision_numeracion referencia contrato_alquiler inexistente: %', NEW.id_entidad;
            END IF;
        WHEN 'instrumento_compraventa' THEN
            IF NOT EXISTS (SELECT 1 FROM instrumento_compraventa WHERE id_instrumento_compraventa = NEW.id_entidad) THEN
                RAISE EXCEPTION 'emision_numeracion referencia instrumento_compraventa inexistente: %', NEW.id_entidad;
            END IF;
        WHEN 'movimiento_financiero' THEN
            IF NOT EXISTS (SELECT 1 FROM movimiento_financiero WHERE id_movimiento_financiero = NEW.id_entidad) THEN
                RAISE EXCEPTION 'emision_numeracion referencia movimiento_financiero inexistente: %', NEW.id_entidad;
            END IF;
    END CASE;

    RETURN NEW;
END;
$$;


--
-- Name: trg_historial_acceso_instalacion_sucursal(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.trg_historial_acceso_instalacion_sucursal() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    PERFORM fn_assert_instalacion_pertenece_a_sucursal(
        NEW.id_instalacion_contexto,
        NEW.id_sucursal_contexto,
        'historial_acceso'
    );
    RETURN NEW;
END;
$$;


--
-- Name: trg_historial_acceso_usuario_sesion(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.trg_historial_acceso_usuario_sesion() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_id_usuario_sesion BIGINT;
BEGIN
    IF NEW.id_sesion_usuario IS NULL THEN
        RETURN NEW;
    END IF;

    SELECT s.id_usuario
      INTO v_id_usuario_sesion
      FROM sesion_usuario s
     WHERE s.id_sesion_usuario = NEW.id_sesion_usuario;

    IF v_id_usuario_sesion IS NULL THEN
        RAISE EXCEPTION 'Sesion inexistente en historial_acceso: %', NEW.id_sesion_usuario;
    END IF;

    IF NEW.id_usuario <> v_id_usuario_sesion THEN
        RAISE EXCEPTION 'Inconsistencia usuario/sesion en historial_acceso: usuario % no coincide con sesion % (usuario %)',
            NEW.id_usuario, NEW.id_sesion_usuario, v_id_usuario_sesion;
    END IF;

    RETURN NEW;
END;
$$;


--
-- Name: trg_inmueble_sucursal_no_solapada(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.trg_inmueble_sucursal_no_solapada() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM inmueble_sucursal x
        WHERE x.id_inmueble_sucursal <> COALESCE(NEW.id_inmueble_sucursal, -1)
          AND x.id_inmueble = NEW.id_inmueble
          AND x.id_sucursal = NEW.id_sucursal
          AND x.deleted_at IS NULL
          AND fn_ranges_overlap(x.fecha_desde, x.fecha_hasta, NEW.fecha_desde, NEW.fecha_hasta)
    ) THEN
        RAISE EXCEPTION 'Solapamiento de vigencia en inmueble_sucursal para inmueble %, sucursal %',
            NEW.id_inmueble, NEW.id_sucursal;
    END IF;

    RETURN NEW;
END;
$$;


--
-- Name: trg_lock_logico_no_solapado(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.trg_lock_logico_no_solapado() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM lock_logico x
        WHERE x.id_lock_logico <> COALESCE(NEW.id_lock_logico, -1)
          AND x.tipo_entidad = NEW.tipo_entidad
          AND x.uid_entidad = NEW.uid_entidad
          AND x.estado_lock = 'ACTIVO'
          AND NEW.estado_lock = 'ACTIVO'
          AND fn_ranges_overlap(
                x.fecha_hora_lock,
                x.fecha_hora_expiracion,
                NEW.fecha_hora_lock,
                NEW.fecha_hora_expiracion
          )
    ) THEN
        RAISE EXCEPTION 'Ya existe lock_logico activo solapado para entidad % / %',
            NEW.tipo_entidad, NEW.uid_entidad;
    END IF;

    RETURN NEW;
END;
$$;


--
-- Name: trg_ocupacion_no_solapada(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.trg_ocupacion_no_solapada() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM ocupacion x
        WHERE x.id_ocupacion <> COALESCE(NEW.id_ocupacion, -1)
          AND COALESCE(x.id_inmueble, -1) = COALESCE(NEW.id_inmueble, -1)
          AND COALESCE(x.id_unidad_funcional, -1) = COALESCE(NEW.id_unidad_funcional, -1)
          AND x.tipo_ocupacion = NEW.tipo_ocupacion
          AND x.deleted_at IS NULL
          AND fn_ranges_overlap(x.fecha_desde, x.fecha_hasta, NEW.fecha_desde, NEW.fecha_hasta)
    ) THEN
        RAISE EXCEPTION 'Solapamiento de vigencia en ocupacion para inmueble %, unidad_funcional %, tipo %',
            NEW.id_inmueble, NEW.id_unidad_funcional, NEW.tipo_ocupacion;
    END IF;

    RETURN NEW;
END;
$$;


--
-- Name: trg_persona_contacto_no_solapado(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.trg_persona_contacto_no_solapado() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    IF NEW.fecha_desde IS NULL THEN
        RETURN NEW;
    END IF;

    IF EXISTS (
        SELECT 1
        FROM persona_contacto x
        WHERE x.id_persona_contacto <> COALESCE(NEW.id_persona_contacto, -1)
          AND x.id_persona = NEW.id_persona
          AND COALESCE(x.tipo_contacto, '') = COALESCE(NEW.tipo_contacto, '')
          AND COALESCE(x.valor_contacto, '') = COALESCE(NEW.valor_contacto, '')
          AND x.deleted_at IS NULL
          AND fn_ranges_overlap_date(x.fecha_desde, x.fecha_hasta, NEW.fecha_desde, NEW.fecha_hasta)
    ) THEN
        RAISE EXCEPTION 'Solapamiento de vigencia en persona_contacto para persona %, tipo %, valor %',
            NEW.id_persona, NEW.tipo_contacto, NEW.valor_contacto;
    END IF;

    RETURN NEW;
END;
$$;


--
-- Name: trg_persona_documento_no_solapado(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.trg_persona_documento_no_solapado() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    IF NEW.fecha_desde IS NULL THEN
        RETURN NEW;
    END IF;

    IF EXISTS (
        SELECT 1
        FROM persona_documento x
        WHERE x.id_persona_documento <> COALESCE(NEW.id_persona_documento, -1)
          AND x.id_persona = NEW.id_persona
          AND COALESCE(x.tipo_documento_persona, '') = COALESCE(NEW.tipo_documento_persona, '')
          AND COALESCE(x.numero_documento, '') = COALESCE(NEW.numero_documento, '')
          AND x.deleted_at IS NULL
          AND fn_ranges_overlap_date(x.fecha_desde, x.fecha_hasta, NEW.fecha_desde, NEW.fecha_hasta)
    ) THEN
        RAISE EXCEPTION 'Solapamiento de vigencia en persona_documento para persona %, tipo %, numero %',
            NEW.id_persona, NEW.tipo_documento_persona, NEW.numero_documento;
    END IF;

    RETURN NEW;
END;
$$;


--
-- Name: trg_persona_domicilio_no_solapado(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.trg_persona_domicilio_no_solapado() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    IF NEW.fecha_desde IS NULL THEN
        RETURN NEW;
    END IF;

    IF EXISTS (
        SELECT 1
        FROM persona_domicilio x
        WHERE x.id_persona_domicilio <> COALESCE(NEW.id_persona_domicilio, -1)
          AND x.id_persona = NEW.id_persona
          AND COALESCE(x.tipo_domicilio, '') = COALESCE(NEW.tipo_domicilio, '')
          AND COALESCE(x.direccion, '') = COALESCE(NEW.direccion, '')
          AND x.deleted_at IS NULL
          AND fn_ranges_overlap_date(x.fecha_desde, x.fecha_hasta, NEW.fecha_desde, NEW.fecha_hasta)
    ) THEN
        RAISE EXCEPTION 'Solapamiento de vigencia en persona_domicilio para persona %, tipo %, direccion %',
            NEW.id_persona, NEW.tipo_domicilio, NEW.direccion;
    END IF;

    RETURN NEW;
END;
$$;


--
-- Name: trg_persona_relacion_no_solapada(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.trg_persona_relacion_no_solapada() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM persona_relacion x
        WHERE x.id_persona_relacion <> COALESCE(NEW.id_persona_relacion, -1)
          AND x.id_persona_origen = NEW.id_persona_origen
          AND x.id_persona_destino = NEW.id_persona_destino
          AND x.tipo_relacion = NEW.tipo_relacion
          AND x.deleted_at IS NULL
          AND fn_ranges_overlap(x.fecha_desde, x.fecha_hasta, NEW.fecha_desde, NEW.fecha_hasta)
    ) THEN
        RAISE EXCEPTION 'Solapamiento de vigencia en persona_relacion para origen %, destino %, tipo %',
            NEW.id_persona_origen, NEW.id_persona_destino, NEW.tipo_relacion;
    END IF;

    RETURN NEW;
END;
$$;


--
-- Name: trg_relacion_generadora_polimorfica(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.trg_relacion_generadora_polimorfica() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    IF NEW.tipo_origen NOT IN ('venta', 'contrato_alquiler') THEN
        RAISE EXCEPTION 'tipo_origen no permitido en relacion_generadora: %', NEW.tipo_origen;
    END IF;

    CASE NEW.tipo_origen
        WHEN 'venta' THEN
            IF NOT EXISTS (SELECT 1 FROM venta WHERE id_venta = NEW.id_origen) THEN
                RAISE EXCEPTION 'relacion_generadora referencia venta inexistente: %', NEW.id_origen;
            END IF;
        WHEN 'contrato_alquiler' THEN
            IF NOT EXISTS (SELECT 1 FROM contrato_alquiler WHERE id_contrato_alquiler = NEW.id_origen) THEN
                RAISE EXCEPTION 'relacion_generadora referencia contrato_alquiler inexistente: %', NEW.id_origen;
            END IF;
    END CASE;

    RETURN NEW;
END;
$$;


--
-- Name: trg_relacion_persona_rol_no_solapada(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.trg_relacion_persona_rol_no_solapada() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM relacion_persona_rol x
        WHERE x.id_relacion_persona_rol <> COALESCE(NEW.id_relacion_persona_rol, -1)
          AND x.id_persona = NEW.id_persona
          AND x.id_rol_participacion = NEW.id_rol_participacion
          AND x.tipo_relacion = NEW.tipo_relacion
          AND x.id_relacion = NEW.id_relacion
          AND x.deleted_at IS NULL
          AND fn_ranges_overlap(x.fecha_desde, x.fecha_hasta, NEW.fecha_desde, NEW.fecha_hasta)
    ) THEN
        RAISE EXCEPTION 'Solapamiento de vigencia en relacion_persona_rol para persona %, rol %, tipo %, id_relacion %',
            NEW.id_persona, NEW.id_rol_participacion, NEW.tipo_relacion, NEW.id_relacion;
    END IF;

    RETURN NEW;
END;
$$;


--
-- Name: trg_relacion_persona_rol_polimorfica(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.trg_relacion_persona_rol_polimorfica() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    IF NEW.tipo_relacion NOT IN (
        'venta',
        'contrato_alquiler',
        'cesion',
        'escrituracion',
        'reserva_venta',
        'reserva_locativa'
    ) THEN
        RAISE EXCEPTION 'tipo_relacion no permitido en relacion_persona_rol: %', NEW.tipo_relacion;
    END IF;

    CASE NEW.tipo_relacion
        WHEN 'venta' THEN
            IF NOT EXISTS (SELECT 1 FROM venta WHERE id_venta = NEW.id_relacion) THEN
                RAISE EXCEPTION 'relacion_persona_rol referencia venta inexistente: %', NEW.id_relacion;
            END IF;
        WHEN 'contrato_alquiler' THEN
            IF NOT EXISTS (SELECT 1 FROM contrato_alquiler WHERE id_contrato_alquiler = NEW.id_relacion) THEN
                RAISE EXCEPTION 'relacion_persona_rol referencia contrato_alquiler inexistente: %', NEW.id_relacion;
            END IF;
        WHEN 'cesion' THEN
            IF NOT EXISTS (SELECT 1 FROM cesion WHERE id_cesion = NEW.id_relacion) THEN
                RAISE EXCEPTION 'relacion_persona_rol referencia cesion inexistente: %', NEW.id_relacion;
            END IF;
        WHEN 'escrituracion' THEN
            IF NOT EXISTS (SELECT 1 FROM escrituracion WHERE id_escrituracion = NEW.id_relacion) THEN
                RAISE EXCEPTION 'relacion_persona_rol referencia escrituracion inexistente: %', NEW.id_relacion;
            END IF;
        WHEN 'reserva_venta' THEN
            IF NOT EXISTS (SELECT 1 FROM reserva_venta WHERE id_reserva_venta = NEW.id_relacion) THEN
                RAISE EXCEPTION 'relacion_persona_rol referencia reserva_venta inexistente: %', NEW.id_relacion;
            END IF;
        WHEN 'reserva_locativa' THEN
            IF NOT EXISTS (SELECT 1 FROM reserva_locativa WHERE id_reserva_locativa = NEW.id_relacion) THEN
                RAISE EXCEPTION 'relacion_persona_rol referencia reserva_locativa inexistente: %', NEW.id_relacion;
            END IF;
    END CASE;

    RETURN NEW;
END;
$$;


--
-- Name: trg_representacion_poder_no_solapada(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.trg_representacion_poder_no_solapada() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM representacion_poder x
        WHERE x.id_representacion_poder <> COALESCE(NEW.id_representacion_poder, -1)
          AND x.id_persona_representado = NEW.id_persona_representado
          AND x.id_persona_representante = NEW.id_persona_representante
          AND COALESCE(x.tipo_poder, '') = COALESCE(NEW.tipo_poder, '')
          AND x.deleted_at IS NULL
          AND fn_ranges_overlap(x.fecha_desde, x.fecha_hasta, NEW.fecha_desde, NEW.fecha_hasta)
    ) THEN
        RAISE EXCEPTION 'Solapamiento de vigencia en representacion_poder para representado %, representante %, tipo %',
            NEW.id_persona_representado, NEW.id_persona_representante, COALESCE(NEW.tipo_poder, '<null>');
    END IF;

    RETURN NEW;
END;
$$;


--
-- Name: trg_sesion_usuario_instalacion_sucursal(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.trg_sesion_usuario_instalacion_sucursal() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    PERFORM fn_assert_instalacion_pertenece_a_sucursal(
        NEW.id_instalacion_origen,
        NEW.id_sucursal_operativa,
        'sesion_usuario'
    );
    RETURN NEW;
END;
$$;


--
-- Name: trg_sincronizacion_operacion_uid_vs_id(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.trg_sincronizacion_operacion_uid_vs_id() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    IF NEW.uid_entidad IS NULL AND NEW.id_entidad_principal IS NULL THEN
        RAISE EXCEPTION 'sincronizacion_operacion requiere uid_entidad o id_entidad_principal';
    END IF;
    RETURN NEW;
END;
$$;


--
-- Name: trg_sincronizacion_paquete_instalacion_valida(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.trg_sincronizacion_paquete_instalacion_valida() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM instalacion i WHERE i.id_instalacion = NEW.id_instalacion_origen
    ) THEN
        RAISE EXCEPTION 'Instalacion origen inexistente en sincronizacion_paquete: %', NEW.id_instalacion_origen;
    END IF;
    RETURN NEW;
END;
$$;


--
-- Name: trg_sincronizacion_recepcion_conflicto_consistente(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.trg_sincronizacion_recepcion_conflicto_consistente() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
DECLARE
    v_op_id VARCHAR(100);
BEGIN
    IF NEW.id_conflicto_sincronizacion IS NULL THEN
        RETURN NEW;
    END IF;

    SELECT c.op_id
      INTO v_op_id
      FROM conflicto_sincronizacion c
     WHERE c.id_conflicto_sincronizacion = NEW.id_conflicto_sincronizacion;

    IF v_op_id IS NULL THEN
        RAISE EXCEPTION 'conflicto_sincronizacion inexistente en sincronizacion_recepcion: %', NEW.id_conflicto_sincronizacion;
    END IF;

    IF v_op_id <> NEW.op_id THEN
        RAISE EXCEPTION 'sincronizacion_recepcion inconsistente: conflicto % no corresponde a op_id %',
            NEW.id_conflicto_sincronizacion, NEW.op_id;
    END IF;

    RETURN NEW;
END;
$$;


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: ajuste_alquiler; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.ajuste_alquiler (
    id_ajuste_alquiler bigint NOT NULL,
    uid_global uuid DEFAULT gen_random_uuid() NOT NULL,
    version_registro integer DEFAULT 1 NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    deleted_at timestamp without time zone,
    id_instalacion_origen bigint,
    id_instalacion_ultima_modificacion bigint,
    op_id_alta uuid,
    op_id_ultima_modificacion uuid,
    id_contrato_alquiler bigint NOT NULL,
    tipo_ajuste character varying(50) NOT NULL,
    valor_ajuste numeric(14,6),
    fecha_aplicacion date NOT NULL,
    descripcion text
);


--
-- Name: ajuste_alquiler_id_ajuste_alquiler_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.ajuste_alquiler_id_ajuste_alquiler_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: ajuste_alquiler_id_ajuste_alquiler_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.ajuste_alquiler_id_ajuste_alquiler_seq OWNED BY public.ajuste_alquiler.id_ajuste_alquiler;


--
-- Name: alcance_autorizacion; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.alcance_autorizacion (
    id_alcance_autorizacion bigint NOT NULL,
    id_rol_seguridad bigint NOT NULL,
    tipo_entidad character varying(50),
    id_entidad bigint,
    nivel_acceso character varying(50)
);


--
-- Name: alcance_autorizacion_id_alcance_autorizacion_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.alcance_autorizacion_id_alcance_autorizacion_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: alcance_autorizacion_id_alcance_autorizacion_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.alcance_autorizacion_id_alcance_autorizacion_seq OWNED BY public.alcance_autorizacion.id_alcance_autorizacion;


--
-- Name: alcance_parametro; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.alcance_parametro (
    id_alcance_parametro bigint NOT NULL,
    codigo_alcance character varying(50) NOT NULL,
    nombre_alcance character varying(150) NOT NULL
);


--
-- Name: alcance_parametro_id_alcance_parametro_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.alcance_parametro_id_alcance_parametro_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: alcance_parametro_id_alcance_parametro_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.alcance_parametro_id_alcance_parametro_seq OWNED BY public.alcance_parametro.id_alcance_parametro;


--
-- Name: aplicacion_financiera; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.aplicacion_financiera (
    id_aplicacion_financiera bigint NOT NULL,
    uid_global uuid DEFAULT gen_random_uuid() NOT NULL,
    version_registro integer DEFAULT 1 NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    deleted_at timestamp without time zone,
    id_instalacion_origen bigint,
    id_instalacion_ultima_modificacion bigint,
    op_id_alta uuid,
    op_id_ultima_modificacion uuid,
    id_movimiento_financiero bigint NOT NULL,
    id_obligacion_financiera bigint NOT NULL,
    id_composicion_obligacion bigint,
    fecha_aplicacion timestamp without time zone NOT NULL,
    tipo_aplicacion character varying(50),
    orden_aplicacion integer,
    importe_aplicado numeric(14,2) NOT NULL,
    id_usuario_aplicador bigint,
    origen_automatico_o_manual character varying(30),
    observaciones text,
    CONSTRAINT chk_aplicacion_financiera_importe CHECK ((importe_aplicado >= (0)::numeric))
);


--
-- Name: aplicacion_financiera_id_aplicacion_financiera_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.aplicacion_financiera_id_aplicacion_financiera_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: aplicacion_financiera_id_aplicacion_financiera_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.aplicacion_financiera_id_aplicacion_financiera_seq OWNED BY public.aplicacion_financiera.id_aplicacion_financiera;


--
-- Name: archivo_digital; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.archivo_digital (
    id_archivo_digital bigint NOT NULL,
    uid_global uuid DEFAULT gen_random_uuid() NOT NULL,
    version_registro integer DEFAULT 1 NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    deleted_at timestamp without time zone,
    id_instalacion_origen bigint,
    id_instalacion_ultima_modificacion bigint,
    op_id_alta uuid,
    op_id_ultima_modificacion uuid,
    id_documento_version bigint NOT NULL,
    nombre_archivo character varying(200),
    ruta_archivo text,
    tipo_mime character varying(100),
    hash_archivo character varying(128),
    tamano_bytes bigint,
    fecha_carga timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    observaciones text
);


--
-- Name: archivo_digital_id_archivo_digital_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.archivo_digital_id_archivo_digital_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: archivo_digital_id_archivo_digital_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.archivo_digital_id_archivo_digital_seq OWNED BY public.archivo_digital.id_archivo_digital;


--
-- Name: cartera_locativa; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.cartera_locativa (
    id_cartera_locativa bigint NOT NULL,
    uid_global uuid DEFAULT gen_random_uuid() NOT NULL,
    version_registro integer DEFAULT 1 NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    deleted_at timestamp without time zone,
    id_instalacion_origen bigint,
    id_instalacion_ultima_modificacion bigint,
    op_id_alta uuid,
    op_id_ultima_modificacion uuid,
    id_inmueble bigint,
    id_unidad_funcional bigint,
    codigo_cartera character varying(50) NOT NULL,
    nombre_cartera character varying(150),
    estado_cartera character varying(30) NOT NULL,
    observaciones text,
    CONSTRAINT chk_cartera_locativa_xor CHECK ((((id_inmueble IS NOT NULL) AND (id_unidad_funcional IS NULL)) OR ((id_inmueble IS NULL) AND (id_unidad_funcional IS NOT NULL))))
);


--
-- Name: cartera_locativa_id_cartera_locativa_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.cartera_locativa_id_cartera_locativa_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: cartera_locativa_id_cartera_locativa_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.cartera_locativa_id_cartera_locativa_seq OWNED BY public.cartera_locativa.id_cartera_locativa;


--
-- Name: catalogo_maestro; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.catalogo_maestro (
    id_catalogo_maestro bigint NOT NULL,
    codigo_catalogo_maestro character varying(50) NOT NULL,
    nombre_catalogo_maestro character varying(150) NOT NULL,
    descripcion text
);


--
-- Name: catalogo_maestro_id_catalogo_maestro_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.catalogo_maestro_id_catalogo_maestro_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: catalogo_maestro_id_catalogo_maestro_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.catalogo_maestro_id_catalogo_maestro_seq OWNED BY public.catalogo_maestro.id_catalogo_maestro;


--
-- Name: cesion; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.cesion (
    id_cesion bigint NOT NULL,
    uid_global uuid DEFAULT gen_random_uuid() NOT NULL,
    version_registro integer DEFAULT 1 NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    deleted_at timestamp without time zone,
    id_instalacion_origen bigint,
    id_instalacion_ultima_modificacion bigint,
    op_id_alta uuid,
    op_id_ultima_modificacion uuid,
    id_venta bigint NOT NULL,
    fecha_cesion timestamp without time zone NOT NULL,
    tipo_cesion character varying(50),
    observaciones text
);


--
-- Name: cesion_id_cesion_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.cesion_id_cesion_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: cesion_id_cesion_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.cesion_id_cesion_seq OWNED BY public.cesion.id_cesion;


--
-- Name: cliente_comprador; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.cliente_comprador (
    id_cliente_comprador bigint NOT NULL,
    uid_global uuid DEFAULT gen_random_uuid() NOT NULL,
    version_registro integer DEFAULT 1 NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    deleted_at timestamp without time zone,
    id_instalacion_origen bigint,
    id_instalacion_ultima_modificacion bigint,
    op_id_alta uuid,
    op_id_ultima_modificacion uuid,
    id_persona bigint NOT NULL,
    codigo_cliente_comprador character varying(50),
    fecha_alta date DEFAULT CURRENT_DATE NOT NULL,
    estado_cliente_comprador character varying(50) DEFAULT 'ACTIVO'::character varying NOT NULL,
    observaciones text
);


--
-- Name: cliente_comprador_id_cliente_comprador_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.cliente_comprador_id_cliente_comprador_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: cliente_comprador_id_cliente_comprador_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.cliente_comprador_id_cliente_comprador_seq OWNED BY public.cliente_comprador.id_cliente_comprador;


--
-- Name: composicion_obligacion; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.composicion_obligacion (
    id_composicion_obligacion bigint NOT NULL,
    uid_global uuid DEFAULT gen_random_uuid() NOT NULL,
    version_registro integer DEFAULT 1 NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    deleted_at timestamp without time zone,
    id_instalacion_origen bigint,
    id_instalacion_ultima_modificacion bigint,
    op_id_alta uuid,
    op_id_ultima_modificacion uuid,
    id_obligacion_financiera bigint NOT NULL,
    id_concepto_financiero bigint NOT NULL,
    orden_composicion integer DEFAULT 1 NOT NULL,
    estado_composicion_obligacion character varying(30) DEFAULT 'ACTIVA'::character varying NOT NULL,
    importe_componente numeric(14,2) NOT NULL,
    saldo_componente numeric(14,2) NOT NULL,
    moneda_componente character varying(10) DEFAULT 'ARS'::character varying NOT NULL,
    detalle_calculo text,
    observaciones text,
    CONSTRAINT chk_composicion_deleted_at CHECK (((deleted_at IS NULL) OR (deleted_at >= created_at))),
    CONSTRAINT chk_composicion_estado CHECK (((estado_composicion_obligacion)::text = ANY ((ARRAY['ACTIVA'::character varying, 'CANCELADA'::character varying, 'ANULADA'::character varying])::text[]))),
    CONSTRAINT chk_composicion_importes_no_negativos CHECK (((importe_componente >= (0)::numeric) AND (saldo_componente >= (0)::numeric))),
    CONSTRAINT chk_composicion_orden_positivo CHECK ((orden_composicion > 0)),
    CONSTRAINT chk_composicion_saldo_no_supera_importe CHECK ((saldo_componente <= importe_componente))
);


--
-- Name: composicion_obligacion_id_composicion_obligacion_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.composicion_obligacion_id_composicion_obligacion_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: composicion_obligacion_id_composicion_obligacion_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.composicion_obligacion_id_composicion_obligacion_seq OWNED BY public.composicion_obligacion.id_composicion_obligacion;


--
-- Name: concepto_financiero; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.concepto_financiero (
    id_concepto_financiero bigint NOT NULL,
    uid_global uuid DEFAULT gen_random_uuid() NOT NULL,
    version_registro integer DEFAULT 1 NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    deleted_at timestamp without time zone,
    id_instalacion_origen bigint,
    id_instalacion_ultima_modificacion bigint,
    op_id_alta uuid,
    op_id_ultima_modificacion uuid,
    codigo_concepto_financiero character varying(50) NOT NULL,
    nombre_concepto_financiero character varying(150) NOT NULL,
    descripcion_concepto_financiero text,
    tipo_concepto_financiero character varying(50) NOT NULL,
    naturaleza_concepto character varying(50) NOT NULL,
    afecta_capital boolean DEFAULT false NOT NULL,
    afecta_interes boolean DEFAULT false NOT NULL,
    afecta_mora boolean DEFAULT false NOT NULL,
    afecta_impuesto boolean DEFAULT false NOT NULL,
    afecta_caja boolean DEFAULT true NOT NULL,
    es_imputable boolean DEFAULT true NOT NULL,
    permite_saldo boolean DEFAULT true NOT NULL,
    estado_concepto_financiero character varying(30) DEFAULT 'ACTIVO'::character varying NOT NULL,
    observaciones text,
    CONSTRAINT chk_concepto_financiero_deleted_at CHECK (((deleted_at IS NULL) OR (deleted_at >= created_at))),
    CONSTRAINT chk_concepto_financiero_estado CHECK (((estado_concepto_financiero)::text = ANY ((ARRAY['ACTIVO'::character varying, 'INACTIVO'::character varying, 'ANULADO'::character varying])::text[])))
);


--
-- Name: concepto_financiero_id_concepto_financiero_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.concepto_financiero_id_concepto_financiero_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: concepto_financiero_id_concepto_financiero_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.concepto_financiero_id_concepto_financiero_seq OWNED BY public.concepto_financiero.id_concepto_financiero;


--
-- Name: conciliacion_bancaria; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.conciliacion_bancaria (
    id_conciliacion_bancaria bigint NOT NULL,
    uid_global uuid DEFAULT gen_random_uuid() NOT NULL,
    version_registro integer DEFAULT 1 NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    deleted_at timestamp without time zone,
    id_instalacion_origen bigint,
    id_instalacion_ultima_modificacion bigint,
    op_id_alta uuid,
    op_id_ultima_modificacion uuid,
    id_cuenta_financiera bigint NOT NULL,
    fecha_conciliacion date NOT NULL,
    saldo_inicial_periodo numeric(14,2),
    saldo_final_periodo numeric(14,2),
    estado character varying(30),
    observaciones text
);


--
-- Name: conciliacion_bancaria_id_conciliacion_bancaria_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.conciliacion_bancaria_id_conciliacion_bancaria_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: conciliacion_bancaria_id_conciliacion_bancaria_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.conciliacion_bancaria_id_conciliacion_bancaria_seq OWNED BY public.conciliacion_bancaria.id_conciliacion_bancaria;


--
-- Name: condicion_economica_alquiler; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.condicion_economica_alquiler (
    id_condicion_economica bigint NOT NULL,
    uid_global uuid DEFAULT gen_random_uuid() NOT NULL,
    version_registro integer DEFAULT 1 NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    deleted_at timestamp without time zone,
    id_instalacion_origen bigint,
    id_instalacion_ultima_modificacion bigint,
    op_id_alta uuid,
    op_id_ultima_modificacion uuid,
    id_contrato_alquiler bigint NOT NULL,
    monto_base numeric(14,2) NOT NULL,
    periodicidad character varying(30),
    moneda character varying(10),
    fecha_desde date NOT NULL,
    fecha_hasta date,
    observaciones text,
    CONSTRAINT chk_condicion_economica_alquiler_vigencia CHECK (((fecha_hasta IS NULL) OR (fecha_hasta >= fecha_desde)))
);


--
-- Name: condicion_economica_alquiler_id_condicion_economica_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.condicion_economica_alquiler_id_condicion_economica_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: condicion_economica_alquiler_id_condicion_economica_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.condicion_economica_alquiler_id_condicion_economica_seq OWNED BY public.condicion_economica_alquiler.id_condicion_economica;


--
-- Name: configuracion_general; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.configuracion_general (
    id_configuracion_general bigint NOT NULL,
    codigo_configuracion character varying(50) NOT NULL,
    nombre_configuracion character varying(150) NOT NULL,
    descripcion text,
    valor_configuracion text,
    estado_configuracion character varying(30)
);


--
-- Name: configuracion_general_id_configuracion_general_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.configuracion_general_id_configuracion_general_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: configuracion_general_id_configuracion_general_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.configuracion_general_id_configuracion_general_seq OWNED BY public.configuracion_general.id_configuracion_general;


--
-- Name: conflicto_sincronizacion; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.conflicto_sincronizacion (
    id_conflicto_sincronizacion bigint NOT NULL,
    op_id character varying(100) NOT NULL,
    uid_entidad uuid,
    tipo_entidad character varying(50) NOT NULL,
    id_entidad bigint,
    version_registro integer,
    tipo_conflicto character varying(50) NOT NULL,
    descripcion text,
    estado_conflicto character varying(50) NOT NULL,
    fecha_detectado timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    fecha_resolucion timestamp without time zone,
    resolucion text,
    CONSTRAINT chk_conflicto_fecha_resolucion CHECK (((fecha_resolucion IS NULL) OR (fecha_resolucion >= fecha_detectado))),
    CONSTRAINT chk_conflicto_version_registro CHECK (((version_registro IS NULL) OR (version_registro >= 1)))
);


--
-- Name: conflicto_sincronizacion_id_conflicto_sincronizacion_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.conflicto_sincronizacion_id_conflicto_sincronizacion_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: conflicto_sincronizacion_id_conflicto_sincronizacion_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.conflicto_sincronizacion_id_conflicto_sincronizacion_seq OWNED BY public.conflicto_sincronizacion.id_conflicto_sincronizacion;


--
-- Name: contrato_alquiler; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.contrato_alquiler (
    id_contrato_alquiler bigint NOT NULL,
    uid_global uuid DEFAULT gen_random_uuid() NOT NULL,
    version_registro integer DEFAULT 1 NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    deleted_at timestamp without time zone,
    id_instalacion_origen bigint,
    id_instalacion_ultima_modificacion bigint,
    op_id_alta uuid,
    op_id_ultima_modificacion uuid,
    id_reserva_locativa bigint,
    id_cartera_locativa bigint,
    id_contrato_anterior bigint,
    codigo_contrato character varying(50) NOT NULL,
    fecha_inicio date NOT NULL,
    fecha_fin date,
    estado_contrato character varying(30) NOT NULL,
    observaciones text,
    CONSTRAINT chk_contrato_alquiler_periodo CHECK (((fecha_fin IS NULL) OR (fecha_fin >= fecha_inicio)))
);


--
-- Name: contrato_alquiler_id_contrato_alquiler_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.contrato_alquiler_id_contrato_alquiler_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: contrato_alquiler_id_contrato_alquiler_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.contrato_alquiler_id_contrato_alquiler_seq OWNED BY public.contrato_alquiler.id_contrato_alquiler;


--
-- Name: contrato_objeto_locativo; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.contrato_objeto_locativo (
    id_contrato_objeto bigint NOT NULL,
    uid_global uuid DEFAULT gen_random_uuid() NOT NULL,
    version_registro integer DEFAULT 1 NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    deleted_at timestamp without time zone,
    id_instalacion_origen bigint,
    id_instalacion_ultima_modificacion bigint,
    op_id_alta uuid,
    op_id_ultima_modificacion uuid,
    id_contrato_alquiler bigint NOT NULL,
    id_inmueble bigint,
    id_unidad_funcional bigint,
    observaciones text,
    CONSTRAINT chk_col_xor CHECK ((((id_inmueble IS NOT NULL) AND (id_unidad_funcional IS NULL)) OR ((id_inmueble IS NULL) AND (id_unidad_funcional IS NOT NULL))))
);


--
-- Name: contrato_objeto_locativo_id_contrato_objeto_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.contrato_objeto_locativo_id_contrato_objeto_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: contrato_objeto_locativo_id_contrato_objeto_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.contrato_objeto_locativo_id_contrato_objeto_seq OWNED BY public.contrato_objeto_locativo.id_contrato_objeto;


--
-- Name: credencial_usuario; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.credencial_usuario (
    id_credencial_usuario bigint NOT NULL,
    id_usuario bigint NOT NULL,
    tipo_credencial character varying(50) NOT NULL,
    identificador_credencial character varying(150),
    hash_credencial text NOT NULL,
    algoritmo_hash character varying(100),
    estado_credencial character varying(30) NOT NULL,
    es_credencial_principal boolean DEFAULT false NOT NULL,
    fecha_alta timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    fecha_activacion timestamp without time zone,
    fecha_vencimiento timestamp without time zone,
    fecha_revocacion timestamp without time zone,
    motivo_revocacion text,
    obliga_rotacion boolean DEFAULT false NOT NULL,
    ultimo_cambio_credencial timestamp without time zone,
    intentos_fallidos_acumulados integer DEFAULT 0 NOT NULL,
    ultimo_intento_fallido timestamp without time zone,
    bloqueo_hasta timestamp without time zone,
    requiere_reset boolean DEFAULT false NOT NULL,
    observaciones text
);


--
-- Name: credencial_usuario_id_credencial_usuario_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.credencial_usuario_id_credencial_usuario_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: credencial_usuario_id_credencial_usuario_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.credencial_usuario_id_credencial_usuario_seq OWNED BY public.credencial_usuario.id_credencial_usuario;


--
-- Name: cuenta_financiera; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.cuenta_financiera (
    id_cuenta_financiera bigint NOT NULL,
    uid_global uuid DEFAULT gen_random_uuid() NOT NULL,
    version_registro integer DEFAULT 1 NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    deleted_at timestamp without time zone,
    id_instalacion_origen bigint,
    id_instalacion_ultima_modificacion bigint,
    op_id_alta uuid,
    op_id_ultima_modificacion uuid,
    tipo_cuenta character varying(50),
    nombre_cuenta character varying(150),
    moneda character varying(10),
    id_sucursal_operativa bigint,
    entidad_financiera character varying(150),
    numero_cuenta character varying(100),
    cbu_alias character varying(100),
    estado character varying(30),
    fecha_alta timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    observaciones text,
    CONSTRAINT chk_cuenta_financiera_saldo CHECK (true)
);


--
-- Name: cuenta_financiera_id_cuenta_financiera_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.cuenta_financiera_id_cuenta_financiera_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: cuenta_financiera_id_cuenta_financiera_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.cuenta_financiera_id_cuenta_financiera_seq OWNED BY public.cuenta_financiera.id_cuenta_financiera;


--
-- Name: denegacion_explicita; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.denegacion_explicita (
    id_denegacion_explicita bigint NOT NULL,
    id_usuario bigint NOT NULL,
    id_permiso bigint NOT NULL,
    motivo text
);


--
-- Name: denegacion_explicita_id_denegacion_explicita_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.denegacion_explicita_id_denegacion_explicita_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: denegacion_explicita_id_denegacion_explicita_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.denegacion_explicita_id_denegacion_explicita_seq OWNED BY public.denegacion_explicita.id_denegacion_explicita;


--
-- Name: desarrollo; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.desarrollo (
    id_desarrollo bigint NOT NULL,
    uid_global uuid DEFAULT gen_random_uuid() NOT NULL,
    version_registro integer DEFAULT 1 NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    deleted_at timestamp without time zone,
    id_instalacion_origen bigint,
    id_instalacion_ultima_modificacion bigint,
    op_id_alta uuid,
    op_id_ultima_modificacion uuid,
    codigo_desarrollo character varying(50) NOT NULL,
    nombre_desarrollo character varying(150) NOT NULL,
    descripcion text,
    estado_desarrollo character varying(30) NOT NULL,
    fecha_alta timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    fecha_baja timestamp without time zone,
    observaciones text
);


--
-- Name: desarrollo_id_desarrollo_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.desarrollo_id_desarrollo_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: desarrollo_id_desarrollo_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.desarrollo_id_desarrollo_seq OWNED BY public.desarrollo.id_desarrollo;


--
-- Name: desarrollo_sucursal; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.desarrollo_sucursal (
    id_desarrollo_sucursal bigint NOT NULL,
    uid_global uuid DEFAULT gen_random_uuid() NOT NULL,
    version_registro integer DEFAULT 1 NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    deleted_at timestamp without time zone,
    id_instalacion_origen bigint,
    id_instalacion_ultima_modificacion bigint,
    op_id_alta uuid,
    op_id_ultima_modificacion uuid,
    id_desarrollo bigint NOT NULL,
    id_sucursal bigint NOT NULL,
    fecha_desde timestamp without time zone NOT NULL,
    fecha_hasta timestamp without time zone,
    observaciones text,
    CONSTRAINT chk_desarrollo_sucursal_vigencia CHECK (((fecha_hasta IS NULL) OR (fecha_hasta >= fecha_desde)))
);


--
-- Name: desarrollo_sucursal_id_desarrollo_sucursal_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.desarrollo_sucursal_id_desarrollo_sucursal_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: desarrollo_sucursal_id_desarrollo_sucursal_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.desarrollo_sucursal_id_desarrollo_sucursal_seq OWNED BY public.desarrollo_sucursal.id_desarrollo_sucursal;


--
-- Name: detalle_cambio_auditoria; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.detalle_cambio_auditoria (
    id_detalle_cambio_auditoria bigint NOT NULL,
    id_evento_auditoria bigint NOT NULL,
    campo_modificado character varying(150) NOT NULL,
    valor_anterior text,
    valor_nuevo text
);


--
-- Name: detalle_cambio_auditoria_id_detalle_cambio_auditoria_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.detalle_cambio_auditoria_id_detalle_cambio_auditoria_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: detalle_cambio_auditoria_id_detalle_cambio_auditoria_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.detalle_cambio_auditoria_id_detalle_cambio_auditoria_seq OWNED BY public.detalle_cambio_auditoria.id_detalle_cambio_auditoria;


--
-- Name: detalle_conciliacion; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.detalle_conciliacion (
    id_detalle_conciliacion bigint NOT NULL,
    uid_global uuid DEFAULT gen_random_uuid() NOT NULL,
    version_registro integer DEFAULT 1 NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    deleted_at timestamp without time zone,
    id_instalacion_origen bigint,
    id_instalacion_ultima_modificacion bigint,
    op_id_alta uuid,
    op_id_ultima_modificacion uuid,
    id_conciliacion_bancaria bigint NOT NULL,
    id_movimiento_tesoreria bigint,
    referencia_banco character varying(150),
    importe_banco numeric(14,2),
    estado character varying(30),
    diferencia_importe numeric(14,2),
    observaciones text
);


--
-- Name: detalle_conciliacion_id_detalle_conciliacion_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.detalle_conciliacion_id_detalle_conciliacion_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: detalle_conciliacion_id_detalle_conciliacion_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.detalle_conciliacion_id_detalle_conciliacion_seq OWNED BY public.detalle_conciliacion.id_detalle_conciliacion;


--
-- Name: disponibilidad; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.disponibilidad (
    id_disponibilidad bigint NOT NULL,
    uid_global uuid DEFAULT gen_random_uuid() NOT NULL,
    version_registro integer DEFAULT 1 NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    deleted_at timestamp without time zone,
    id_instalacion_origen bigint,
    id_instalacion_ultima_modificacion bigint,
    op_id_alta uuid,
    op_id_ultima_modificacion uuid,
    id_inmueble bigint,
    id_unidad_funcional bigint,
    estado_disponibilidad character varying(30) NOT NULL,
    fecha_desde timestamp without time zone NOT NULL,
    fecha_hasta timestamp without time zone,
    motivo character varying(200),
    observaciones text,
    CONSTRAINT chk_disponibilidad_vigencia CHECK (((fecha_hasta IS NULL) OR (fecha_hasta >= fecha_desde))),
    CONSTRAINT chk_disponibilidad_xor CHECK ((((id_inmueble IS NOT NULL) AND (id_unidad_funcional IS NULL)) OR ((id_inmueble IS NULL) AND (id_unidad_funcional IS NOT NULL))))
);


--
-- Name: disponibilidad_id_disponibilidad_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.disponibilidad_id_disponibilidad_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: disponibilidad_id_disponibilidad_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.disponibilidad_id_disponibilidad_seq OWNED BY public.disponibilidad.id_disponibilidad;


--
-- Name: documento_entidad; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.documento_entidad (
    id_documento_entidad bigint NOT NULL,
    uid_global uuid DEFAULT gen_random_uuid() NOT NULL,
    version_registro integer DEFAULT 1 NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    deleted_at timestamp without time zone,
    id_instalacion_origen bigint,
    id_instalacion_ultima_modificacion bigint,
    op_id_alta uuid,
    op_id_ultima_modificacion uuid,
    id_documento_logico bigint NOT NULL,
    tipo_entidad character varying(50) NOT NULL,
    id_entidad bigint NOT NULL,
    tipo_relacion character varying(50),
    fecha_asociacion timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    observaciones text
);


--
-- Name: documento_entidad_id_documento_entidad_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.documento_entidad_id_documento_entidad_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: documento_entidad_id_documento_entidad_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.documento_entidad_id_documento_entidad_seq OWNED BY public.documento_entidad.id_documento_entidad;


--
-- Name: documento_logico; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.documento_logico (
    id_documento_logico bigint NOT NULL,
    uid_global uuid DEFAULT gen_random_uuid() NOT NULL,
    version_registro integer DEFAULT 1 NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    deleted_at timestamp without time zone,
    id_instalacion_origen bigint,
    id_instalacion_ultima_modificacion bigint,
    op_id_alta uuid,
    op_id_ultima_modificacion uuid,
    id_tipo_documental bigint NOT NULL,
    codigo_documento character varying(50),
    titulo_documento character varying(200),
    descripcion_documento text,
    estado_documento character varying(30) NOT NULL,
    origen_documento character varying(50),
    confidencialidad character varying(50),
    fecha_creacion timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    fecha_archivado timestamp without time zone,
    id_sucursal_origen bigint,
    id_instalacion_creadora bigint,
    id_usuario_creador bigint,
    observaciones text
);


--
-- Name: documento_logico_id_documento_logico_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.documento_logico_id_documento_logico_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: documento_logico_id_documento_logico_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.documento_logico_id_documento_logico_seq OWNED BY public.documento_logico.id_documento_logico;


--
-- Name: documento_version; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.documento_version (
    id_documento_version bigint NOT NULL,
    uid_global uuid DEFAULT gen_random_uuid() NOT NULL,
    version_registro integer DEFAULT 1 NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    deleted_at timestamp without time zone,
    id_instalacion_origen bigint,
    id_instalacion_ultima_modificacion bigint,
    op_id_alta uuid,
    op_id_ultima_modificacion uuid,
    id_documento_logico bigint NOT NULL,
    numero_version integer NOT NULL,
    fecha_version timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    estado_version character varying(30) NOT NULL,
    es_version_actual boolean DEFAULT false NOT NULL,
    observaciones text,
    CONSTRAINT chk_documento_version_numero CHECK ((numero_version > 0))
);


--
-- Name: documento_version_id_documento_version_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.documento_version_id_documento_version_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: documento_version_id_documento_version_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.documento_version_id_documento_version_seq OWNED BY public.documento_version.id_documento_version;


--
-- Name: edificacion; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.edificacion (
    id_edificacion bigint NOT NULL,
    uid_global uuid DEFAULT gen_random_uuid() NOT NULL,
    version_registro integer DEFAULT 1 NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    deleted_at timestamp without time zone,
    id_instalacion_origen bigint,
    id_instalacion_ultima_modificacion bigint,
    op_id_alta uuid,
    op_id_ultima_modificacion uuid,
    id_inmueble bigint,
    id_unidad_funcional bigint,
    descripcion character varying(200),
    tipo_edificacion character varying(50),
    superficie numeric(14,2),
    fecha_alta timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    observaciones text,
    CONSTRAINT chk_edificacion_xor CHECK ((((id_inmueble IS NOT NULL) AND (id_unidad_funcional IS NULL)) OR ((id_inmueble IS NULL) AND (id_unidad_funcional IS NOT NULL))))
);


--
-- Name: edificacion_id_edificacion_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.edificacion_id_edificacion_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: edificacion_id_edificacion_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.edificacion_id_edificacion_seq OWNED BY public.edificacion.id_edificacion;


--
-- Name: emision_numeracion; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.emision_numeracion (
    id_emision_numeracion bigint NOT NULL,
    uid_global uuid DEFAULT gen_random_uuid() NOT NULL,
    version_registro integer DEFAULT 1 NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    deleted_at timestamp without time zone,
    id_instalacion_origen bigint,
    id_instalacion_ultima_modificacion bigint,
    op_id_alta uuid,
    op_id_ultima_modificacion uuid,
    id_numerador_serie bigint NOT NULL,
    numero_emitido bigint NOT NULL,
    fecha_emision timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    tipo_entidad character varying(50),
    id_entidad bigint,
    estado_emision character varying(30) NOT NULL,
    observaciones text,
    CONSTRAINT chk_emision_numeracion_numero_positivo CHECK ((numero_emitido > 0))
);


--
-- Name: emision_numeracion_id_emision_numeracion_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.emision_numeracion_id_emision_numeracion_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: emision_numeracion_id_emision_numeracion_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.emision_numeracion_id_emision_numeracion_seq OWNED BY public.emision_numeracion.id_emision_numeracion;


--
-- Name: entrega_restitucion_inmueble; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.entrega_restitucion_inmueble (
    id_entrega_restitucion bigint NOT NULL,
    uid_global uuid DEFAULT gen_random_uuid() NOT NULL,
    version_registro integer DEFAULT 1 NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    deleted_at timestamp without time zone,
    id_instalacion_origen bigint,
    id_instalacion_ultima_modificacion bigint,
    op_id_alta uuid,
    op_id_ultima_modificacion uuid,
    id_contrato_alquiler bigint NOT NULL,
    fecha_entrega date NOT NULL,
    estado_inmueble character varying(50),
    observaciones text
);


--
-- Name: entrega_restitucion_inmueble_id_entrega_restitucion_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.entrega_restitucion_inmueble_id_entrega_restitucion_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: entrega_restitucion_inmueble_id_entrega_restitucion_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.entrega_restitucion_inmueble_id_entrega_restitucion_seq OWNED BY public.entrega_restitucion_inmueble.id_entrega_restitucion;


--
-- Name: entrega_locativa_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.entrega_locativa_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: entrega_locativa; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.entrega_locativa (
    id_entrega_locativa bigint NOT NULL DEFAULT nextval('public.entrega_locativa_id_seq'::regclass),
    uid_global uuid DEFAULT gen_random_uuid() NOT NULL,
    version_registro integer DEFAULT 1 NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    deleted_at timestamp without time zone,
    id_instalacion_origen bigint,
    id_instalacion_ultima_modificacion bigint,
    op_id_alta uuid,
    op_id_ultima_modificacion uuid,
    id_contrato_alquiler bigint NOT NULL,
    fecha_entrega date NOT NULL,
    observaciones text,
    CONSTRAINT entrega_locativa_pkey PRIMARY KEY (id_entrega_locativa)
);

ALTER SEQUENCE public.entrega_locativa_id_seq OWNED BY public.entrega_locativa.id_entrega_locativa;


--
-- Name: escrituracion; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.escrituracion (
    id_escrituracion bigint NOT NULL,
    uid_global uuid DEFAULT gen_random_uuid() NOT NULL,
    version_registro integer DEFAULT 1 NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    deleted_at timestamp without time zone,
    id_instalacion_origen bigint,
    id_instalacion_ultima_modificacion bigint,
    op_id_alta uuid,
    op_id_ultima_modificacion uuid,
    id_venta bigint NOT NULL,
    fecha_escrituracion timestamp without time zone NOT NULL,
    numero_escritura character varying(100),
    observaciones text
);


--
-- Name: escrituracion_id_escrituracion_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.escrituracion_id_escrituracion_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: escrituracion_id_escrituracion_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.escrituracion_id_escrituracion_seq OWNED BY public.escrituracion.id_escrituracion;


--
-- Name: outbox_event; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.outbox_event (
    id bigint NOT NULL,
    event_id uuid DEFAULT gen_random_uuid() NOT NULL,
    event_type character varying(100) NOT NULL,
    aggregate_type character varying(100) NOT NULL,
    aggregate_id bigint NOT NULL,
    payload jsonb NOT NULL,
    occurred_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    published_at timestamp without time zone,
    processed_at timestamp without time zone,
    status character varying(20) DEFAULT 'PENDING'::character varying NOT NULL,
    retry_count integer DEFAULT 0 NOT NULL,
    last_error text,
    processing_reason jsonb,
    processing_metadata jsonb
);


--
-- Name: outbox_event_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.outbox_event_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: outbox_event_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.outbox_event_id_seq OWNED BY public.outbox_event.id;


--
-- Name: inbox_event_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.inbox_event_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: inbox_event; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.inbox_event (
    id bigint NOT NULL DEFAULT nextval('public.inbox_event_id_seq'::regclass),
    event_id uuid NOT NULL,
    event_type character varying(100) NOT NULL,
    aggregate_type character varying(100) NOT NULL,
    aggregate_id bigint NOT NULL,
    consumer character varying(100) NOT NULL,
    status character varying(20) DEFAULT 'PROCESSING'::character varying NOT NULL,
    processed_at timestamp without time zone,
    error_detail text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT inbox_event_pkey PRIMARY KEY (id),
    CONSTRAINT uq_inbox_event_consumer UNIQUE (event_id, consumer)
);

ALTER SEQUENCE public.inbox_event_id_seq OWNED BY public.inbox_event.id;

CREATE INDEX idx_inbox_event_lookup ON public.inbox_event USING btree (consumer, status, created_at);


--
-- Name: evento_auditoria; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.evento_auditoria (
    id_evento_auditoria bigint NOT NULL,
    id_usuario bigint,
    id_sucursal bigint,
    id_instalacion bigint,
    id_tipo_evento_auditoria bigint,
    id_resultado_evento_auditoria bigint,
    id_operacion_auditoria bigint,
    tipo_entidad character varying(50),
    id_entidad bigint,
    fecha_hora_evento timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    detalle jsonb
);


--
-- Name: evento_auditoria_id_evento_auditoria_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.evento_auditoria_id_evento_auditoria_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: evento_auditoria_id_evento_auditoria_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.evento_auditoria_id_evento_auditoria_seq OWNED BY public.evento_auditoria.id_evento_auditoria;


--
-- Name: evento_numeracion; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.evento_numeracion (
    id_evento_numeracion bigint NOT NULL,
    uid_global uuid DEFAULT gen_random_uuid() NOT NULL,
    version_registro integer DEFAULT 1 NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    deleted_at timestamp without time zone,
    id_instalacion_origen bigint,
    id_instalacion_ultima_modificacion bigint,
    op_id_alta uuid,
    op_id_ultima_modificacion uuid,
    id_emision_numeracion bigint NOT NULL,
    tipo_evento character varying(50) NOT NULL,
    fecha_evento timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    descripcion text
);


--
-- Name: evento_numeracion_id_evento_numeracion_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.evento_numeracion_id_evento_numeracion_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: evento_numeracion_id_evento_numeracion_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.evento_numeracion_id_evento_numeracion_seq OWNED BY public.evento_numeracion.id_evento_numeracion;


--
-- Name: factura_servicio; Type: TABLE; Schema: public; Owner: -
--
-- Registro estructural de facturas externas de servicios emitidas por proveedores.
-- El sistema no factura servicios ni genera obligaciones financieras desde este dominio.
-- El evento factura_servicio_registrada queda pendiente de contrato/emision real; no existe
-- patron SQL generico de outbox para eventos de dominio en este schema.

CREATE TABLE public.factura_servicio (
    id_factura_servicio bigint NOT NULL,
    uid_global uuid DEFAULT gen_random_uuid() NOT NULL,
    version_registro integer DEFAULT 1 NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    deleted_at timestamp without time zone,
    id_instalacion_origen bigint,
    id_instalacion_ultima_modificacion bigint,
    op_id_alta uuid,
    op_id_ultima_modificacion uuid,
    id_servicio bigint NOT NULL,
    id_inmueble bigint,
    id_unidad_funcional bigint,
    proveedor character varying(150) NOT NULL,
    numero_factura character varying(100) NOT NULL,
    fecha_emision date NOT NULL,
    fecha_vencimiento date,
    periodo_desde date,
    periodo_hasta date,
    importe_total numeric(18,2) NOT NULL,
    estado_factura_servicio character varying(30) DEFAULT 'REGISTRADA'::character varying NOT NULL,
    observaciones text,
    CONSTRAINT chk_factura_servicio_importe_no_negativo CHECK ((importe_total >= (0)::numeric)),
    CONSTRAINT chk_factura_servicio_objeto_xor CHECK ((((id_inmueble IS NOT NULL) AND (id_unidad_funcional IS NULL)) OR ((id_inmueble IS NULL) AND (id_unidad_funcional IS NOT NULL)))),
    CONSTRAINT chk_factura_servicio_periodo CHECK (((periodo_hasta IS NULL) OR (periodo_desde IS NULL) OR (periodo_hasta >= periodo_desde))),
    CONSTRAINT chk_factura_servicio_vencimiento CHECK (((fecha_vencimiento IS NULL) OR (fecha_vencimiento >= fecha_emision)))
);


--
-- Name: factura_servicio_id_factura_servicio_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.factura_servicio_id_factura_servicio_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: factura_servicio_id_factura_servicio_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.factura_servicio_id_factura_servicio_seq OWNED BY public.factura_servicio.id_factura_servicio;


--
-- Name: historial_acceso; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.historial_acceso (
    id_historial_acceso bigint NOT NULL,
    id_usuario bigint NOT NULL,
    id_credencial_usuario bigint,
    id_sesion_usuario bigint,
    id_sucursal_contexto bigint,
    id_instalacion_contexto bigint,
    fecha_hora_evento timestamp without time zone NOT NULL,
    tipo_evento_acceso character varying(50) NOT NULL,
    resultado_evento character varying(50),
    motivo_resultado text,
    detalle_evento text,
    ip_origen character varying(50),
    nombre_equipo_origen character varying(150),
    origen_evento character varying(50),
    es_evento_auditable boolean DEFAULT true NOT NULL,
    observaciones text
);


--
-- Name: historial_acceso_id_historial_acceso_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.historial_acceso_id_historial_acceso_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: historial_acceso_id_historial_acceso_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.historial_acceso_id_historial_acceso_seq OWNED BY public.historial_acceso.id_historial_acceso;


--
-- Name: historial_catalogo; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.historial_catalogo (
    id_historial_catalogo bigint NOT NULL,
    id_catalogo_maestro bigint NOT NULL,
    fecha_hora_cambio timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    descripcion_cambio text
);


--
-- Name: historial_catalogo_id_historial_catalogo_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.historial_catalogo_id_historial_catalogo_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: historial_catalogo_id_historial_catalogo_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.historial_catalogo_id_historial_catalogo_seq OWNED BY public.historial_catalogo.id_historial_catalogo;


--
-- Name: historial_parametro; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.historial_parametro (
    id_historial_parametro bigint NOT NULL,
    id_parametro_sistema bigint NOT NULL,
    fecha_hora_cambio timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    valor_anterior text,
    valor_nuevo text,
    observaciones text
);


--
-- Name: historial_parametro_id_historial_parametro_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.historial_parametro_id_historial_parametro_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: historial_parametro_id_historial_parametro_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.historial_parametro_id_historial_parametro_seq OWNED BY public.historial_parametro.id_historial_parametro;


--
-- Name: inmueble; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.inmueble (
    id_inmueble bigint NOT NULL,
    uid_global uuid DEFAULT gen_random_uuid() NOT NULL,
    version_registro integer DEFAULT 1 NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    deleted_at timestamp without time zone,
    id_instalacion_origen bigint,
    id_instalacion_ultima_modificacion bigint,
    op_id_alta uuid,
    op_id_ultima_modificacion uuid,
    id_desarrollo bigint,
    codigo_inmueble character varying(50) NOT NULL,
    nombre_inmueble character varying(150),
    superficie numeric(14,2),
    estado_administrativo character varying(30) NOT NULL,
    estado_juridico character varying(30) NOT NULL,
    fecha_alta timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    fecha_baja timestamp without time zone,
    observaciones text
);


--
-- Name: inmueble_id_inmueble_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.inmueble_id_inmueble_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: inmueble_id_inmueble_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.inmueble_id_inmueble_seq OWNED BY public.inmueble.id_inmueble;


--
-- Name: inmueble_servicio; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.inmueble_servicio (
    id_inmueble_servicio bigint NOT NULL,
    uid_global uuid DEFAULT gen_random_uuid() NOT NULL,
    version_registro integer DEFAULT 1 NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    deleted_at timestamp without time zone,
    id_instalacion_origen bigint,
    id_instalacion_ultima_modificacion bigint,
    op_id_alta uuid,
    op_id_ultima_modificacion uuid,
    id_inmueble bigint NOT NULL,
    id_servicio bigint NOT NULL,
    estado character varying(30),
    fecha_alta timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: inmueble_servicio_id_inmueble_servicio_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.inmueble_servicio_id_inmueble_servicio_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: inmueble_servicio_id_inmueble_servicio_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.inmueble_servicio_id_inmueble_servicio_seq OWNED BY public.inmueble_servicio.id_inmueble_servicio;


--
-- Name: inmueble_sucursal; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.inmueble_sucursal (
    id_inmueble_sucursal bigint NOT NULL,
    uid_global uuid DEFAULT gen_random_uuid() NOT NULL,
    version_registro integer DEFAULT 1 NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    deleted_at timestamp without time zone,
    id_instalacion_origen bigint,
    id_instalacion_ultima_modificacion bigint,
    op_id_alta uuid,
    op_id_ultima_modificacion uuid,
    id_inmueble bigint NOT NULL,
    id_sucursal bigint NOT NULL,
    fecha_desde timestamp without time zone NOT NULL,
    fecha_hasta timestamp without time zone,
    observaciones text,
    CONSTRAINT chk_inmueble_sucursal_vigencia CHECK (((fecha_hasta IS NULL) OR (fecha_hasta >= fecha_desde)))
);


--
-- Name: inmueble_sucursal_id_inmueble_sucursal_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.inmueble_sucursal_id_inmueble_sucursal_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: inmueble_sucursal_id_inmueble_sucursal_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.inmueble_sucursal_id_inmueble_sucursal_seq OWNED BY public.inmueble_sucursal.id_inmueble_sucursal;


--
-- Name: instalacion; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.instalacion (
    id_instalacion bigint NOT NULL,
    uid_global uuid DEFAULT gen_random_uuid() NOT NULL,
    version_registro integer DEFAULT 1 NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    deleted_at timestamp without time zone,
    id_instalacion_origen bigint,
    id_instalacion_ultima_modificacion bigint,
    op_id_alta uuid,
    op_id_ultima_modificacion uuid,
    id_sucursal bigint NOT NULL,
    codigo_instalacion character varying(50) NOT NULL,
    nombre_instalacion character varying(150) NOT NULL,
    descripcion_instalacion text,
    estado_instalacion character varying(30) NOT NULL,
    es_principal boolean DEFAULT false NOT NULL,
    permite_sincronizacion boolean DEFAULT true NOT NULL,
    identificador_tecnico character varying(150),
    direccion_local character varying(150),
    fecha_alta timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    fecha_baja timestamp without time zone,
    observaciones text,
    CONSTRAINT chk_instalacion_deleted_at CHECK (((deleted_at IS NULL) OR (deleted_at >= created_at)))
);


--
-- Name: instalacion_id_instalacion_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.instalacion_id_instalacion_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: instalacion_id_instalacion_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.instalacion_id_instalacion_seq OWNED BY public.instalacion.id_instalacion;


--
-- Name: instrumento_compraventa; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.instrumento_compraventa (
    id_instrumento_compraventa bigint NOT NULL,
    uid_global uuid DEFAULT gen_random_uuid() NOT NULL,
    version_registro integer DEFAULT 1 NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    deleted_at timestamp without time zone,
    id_instalacion_origen bigint,
    id_instalacion_ultima_modificacion bigint,
    op_id_alta uuid,
    op_id_ultima_modificacion uuid,
    id_venta bigint NOT NULL,
    tipo_instrumento character varying(50) NOT NULL,
    numero_instrumento character varying(100),
    fecha_instrumento timestamp without time zone NOT NULL,
    estado_instrumento character varying(30) NOT NULL,
    observaciones text
);


--
-- Name: instrumento_compraventa_id_instrumento_compraventa_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.instrumento_compraventa_id_instrumento_compraventa_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: instrumento_compraventa_id_instrumento_compraventa_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.instrumento_compraventa_id_instrumento_compraventa_seq OWNED BY public.instrumento_compraventa.id_instrumento_compraventa;


--
-- Name: instrumento_objeto_inmobiliario; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.instrumento_objeto_inmobiliario (
    id_instrumento_objeto bigint NOT NULL,
    uid_global uuid DEFAULT gen_random_uuid() NOT NULL,
    version_registro integer DEFAULT 1 NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    deleted_at timestamp without time zone,
    id_instalacion_origen bigint,
    id_instalacion_ultima_modificacion bigint,
    op_id_alta uuid,
    op_id_ultima_modificacion uuid,
    id_instrumento_compraventa bigint CONSTRAINT instrumento_objeto_inmobili_id_instrumento_compraventa_not_null NOT NULL,
    id_inmueble bigint,
    id_unidad_funcional bigint,
    observaciones text,
    CONSTRAINT chk_io_xor CHECK ((((id_inmueble IS NOT NULL) AND (id_unidad_funcional IS NULL)) OR ((id_inmueble IS NULL) AND (id_unidad_funcional IS NOT NULL))))
);


--
-- Name: instrumento_objeto_inmobiliario_id_instrumento_objeto_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.instrumento_objeto_inmobiliario_id_instrumento_objeto_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: instrumento_objeto_inmobiliario_id_instrumento_objeto_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.instrumento_objeto_inmobiliario_id_instrumento_objeto_seq OWNED BY public.instrumento_objeto_inmobiliario.id_instrumento_objeto;


--
-- Name: item_catalogo; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.item_catalogo (
    id_item_catalogo bigint NOT NULL,
    id_catalogo_maestro bigint NOT NULL,
    codigo_item_catalogo character varying(50) NOT NULL,
    nombre_item_catalogo character varying(150) NOT NULL,
    descripcion text,
    estado_item_catalogo character varying(30)
);


--
-- Name: item_catalogo_id_item_catalogo_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.item_catalogo_id_item_catalogo_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: item_catalogo_id_item_catalogo_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.item_catalogo_id_item_catalogo_seq OWNED BY public.item_catalogo.id_item_catalogo;


--
-- Name: jerarquia_item_catalogo; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.jerarquia_item_catalogo (
    id_jerarquia_item_catalogo bigint NOT NULL,
    id_item_catalogo_padre bigint NOT NULL,
    id_item_catalogo_hijo bigint NOT NULL
);


--
-- Name: jerarquia_item_catalogo_id_jerarquia_item_catalogo_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.jerarquia_item_catalogo_id_jerarquia_item_catalogo_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: jerarquia_item_catalogo_id_jerarquia_item_catalogo_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.jerarquia_item_catalogo_id_jerarquia_item_catalogo_seq OWNED BY public.jerarquia_item_catalogo.id_jerarquia_item_catalogo;


--
-- Name: lock_logico; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.lock_logico (
    id_lock_logico bigint NOT NULL,
    tipo_entidad character varying(100) NOT NULL,
    uid_entidad uuid NOT NULL,
    id_instalacion_origen bigint NOT NULL,
    id_usuario_origen bigint,
    op_id character varying(100),
    motivo_lock character varying(200),
    fecha_hora_lock timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    fecha_hora_expiracion timestamp without time zone,
    estado_lock character varying(50) DEFAULT 'ACTIVO'::character varying NOT NULL,
    observaciones text,
    CONSTRAINT chk_lock_logico_expiracion CHECK (((fecha_hora_expiracion IS NULL) OR (fecha_hora_expiracion >= fecha_hora_lock)))
);


--
-- Name: lock_logico_id_lock_logico_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.lock_logico_id_lock_logico_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: lock_logico_id_lock_logico_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.lock_logico_id_lock_logico_seq OWNED BY public.lock_logico.id_lock_logico;


--
-- Name: modificacion_locativa; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.modificacion_locativa (
    id_modificacion_locativa bigint NOT NULL,
    uid_global uuid DEFAULT gen_random_uuid() NOT NULL,
    version_registro integer DEFAULT 1 NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    deleted_at timestamp without time zone,
    id_instalacion_origen bigint,
    id_instalacion_ultima_modificacion bigint,
    op_id_alta uuid,
    op_id_ultima_modificacion uuid,
    id_contrato_alquiler bigint NOT NULL,
    tipo_modificacion character varying(50) NOT NULL,
    fecha_modificacion timestamp without time zone NOT NULL,
    descripcion text
);


--
-- Name: modificacion_locativa_id_modificacion_locativa_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.modificacion_locativa_id_modificacion_locativa_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: modificacion_locativa_id_modificacion_locativa_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.modificacion_locativa_id_modificacion_locativa_seq OWNED BY public.modificacion_locativa.id_modificacion_locativa;


--
-- Name: movimiento_financiero; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.movimiento_financiero (
    id_movimiento_financiero bigint NOT NULL,
    uid_global uuid DEFAULT gen_random_uuid() NOT NULL,
    version_registro integer DEFAULT 1 NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    deleted_at timestamp without time zone,
    id_instalacion_origen bigint,
    id_instalacion_ultima_modificacion bigint,
    op_id_alta uuid,
    op_id_ultima_modificacion uuid,
    fecha_movimiento timestamp without time zone NOT NULL,
    tipo_movimiento character varying(50) NOT NULL,
    importe numeric(14,2) NOT NULL,
    signo character varying(10) NOT NULL,
    estado_movimiento character varying(30) NOT NULL,
    observaciones text,
    CONSTRAINT chk_movimiento_financiero_importe CHECK ((importe >= (0)::numeric))
);


--
-- Name: movimiento_financiero_id_movimiento_financiero_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.movimiento_financiero_id_movimiento_financiero_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: movimiento_financiero_id_movimiento_financiero_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.movimiento_financiero_id_movimiento_financiero_seq OWNED BY public.movimiento_financiero.id_movimiento_financiero;


--
-- Name: movimiento_tesoreria; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.movimiento_tesoreria (
    id_movimiento_tesoreria bigint NOT NULL,
    uid_global uuid DEFAULT gen_random_uuid() NOT NULL,
    version_registro integer DEFAULT 1 NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    deleted_at timestamp without time zone,
    id_instalacion_origen bigint,
    id_instalacion_ultima_modificacion bigint,
    op_id_alta uuid,
    op_id_ultima_modificacion uuid,
    id_movimiento_financiero bigint,
    id_cuenta_financiera_origen bigint,
    id_cuenta_financiera_destino bigint,
    tipo_movimiento_tesoreria character varying(50),
    fecha_movimiento timestamp without time zone NOT NULL,
    importe numeric(14,2) NOT NULL,
    estado character varying(30),
    id_sucursal_operativa bigint,
    id_usuario_operador bigint,
    referencia_externa character varying(150),
    observaciones text,
    CONSTRAINT chk_movimiento_tesoreria_importe CHECK ((importe >= (0)::numeric)),
    CONSTRAINT chk_mt_al_menos_una_cuenta CHECK (((id_cuenta_financiera_origen IS NOT NULL) OR (id_cuenta_financiera_destino IS NOT NULL)))
);


--
-- Name: movimiento_tesoreria_id_movimiento_tesoreria_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.movimiento_tesoreria_id_movimiento_tesoreria_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: movimiento_tesoreria_id_movimiento_tesoreria_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.movimiento_tesoreria_id_movimiento_tesoreria_seq OWNED BY public.movimiento_tesoreria.id_movimiento_tesoreria;


--
-- Name: numerador_documental; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.numerador_documental (
    id_numerador_documental bigint NOT NULL,
    uid_global uuid DEFAULT gen_random_uuid() NOT NULL,
    version_registro integer DEFAULT 1 NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    deleted_at timestamp without time zone,
    id_instalacion_origen bigint,
    id_instalacion_ultima_modificacion bigint,
    op_id_alta uuid,
    op_id_ultima_modificacion uuid,
    codigo_numerador character varying(50) NOT NULL,
    nombre_numerador character varying(150) NOT NULL,
    tipo_documental_aplicable character varying(50),
    estado_numerador character varying(30) NOT NULL,
    observaciones text
);


--
-- Name: numerador_documental_id_numerador_documental_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.numerador_documental_id_numerador_documental_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: numerador_documental_id_numerador_documental_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.numerador_documental_id_numerador_documental_seq OWNED BY public.numerador_documental.id_numerador_documental;


--
-- Name: numerador_serie; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.numerador_serie (
    id_numerador_serie bigint NOT NULL,
    uid_global uuid DEFAULT gen_random_uuid() NOT NULL,
    version_registro integer DEFAULT 1 NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    deleted_at timestamp without time zone,
    id_instalacion_origen bigint,
    id_instalacion_ultima_modificacion bigint,
    op_id_alta uuid,
    op_id_ultima_modificacion uuid,
    id_numerador_documental bigint NOT NULL,
    codigo_serie character varying(50) NOT NULL,
    id_sucursal bigint NOT NULL,
    numero_actual bigint DEFAULT 0 NOT NULL,
    numero_desde bigint,
    numero_hasta bigint,
    estado_serie character varying(30) NOT NULL,
    fecha_alta timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    observaciones text,
    CONSTRAINT chk_numerador_serie_numero_actual CHECK ((numero_actual >= 0))
);


--
-- Name: numerador_serie_id_numerador_serie_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.numerador_serie_id_numerador_serie_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: numerador_serie_id_numerador_serie_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.numerador_serie_id_numerador_serie_seq OWNED BY public.numerador_serie.id_numerador_serie;


--
-- Name: objeto_auditado; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.objeto_auditado (
    id_objeto_auditado bigint NOT NULL,
    tipo_entidad character varying(50) NOT NULL,
    id_entidad bigint NOT NULL,
    uid_entidad uuid,
    descripcion_objeto text
);


--
-- Name: objeto_auditado_id_objeto_auditado_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.objeto_auditado_id_objeto_auditado_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: objeto_auditado_id_objeto_auditado_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.objeto_auditado_id_objeto_auditado_seq OWNED BY public.objeto_auditado.id_objeto_auditado;


--
-- Name: obligacion_financiera; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.obligacion_financiera (
    id_obligacion_financiera bigint NOT NULL,
    uid_global uuid DEFAULT gen_random_uuid() NOT NULL,
    version_registro integer DEFAULT 1 NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    deleted_at timestamp without time zone,
    id_instalacion_origen bigint,
    id_instalacion_ultima_modificacion bigint,
    op_id_alta uuid,
    op_id_ultima_modificacion uuid,
    id_relacion_generadora bigint NOT NULL,
    codigo_obligacion_financiera character varying(50),
    descripcion_operativa text,
    fecha_generacion timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    fecha_emision date NOT NULL,
    fecha_vencimiento date,
    periodo_desde date,
    periodo_hasta date,
    fecha_cierre timestamp without time zone,
    importe_total numeric(14,2) NOT NULL,
    saldo_pendiente numeric(14,2) NOT NULL,
    importe_cancelado_acumulado numeric(14,2) DEFAULT 0 NOT NULL,
    importe_bonificado_acumulado numeric(14,2) DEFAULT 0 NOT NULL,
    importe_anulado_acumulado numeric(14,2) DEFAULT 0 NOT NULL,
    moneda character varying(10) DEFAULT 'ARS'::character varying NOT NULL,
    estado_obligacion character varying(30) NOT NULL,
    es_exigible boolean DEFAULT false NOT NULL,
    es_proyectada boolean DEFAULT false NOT NULL,
    es_emitida boolean DEFAULT false NOT NULL,
    es_vencida boolean DEFAULT false NOT NULL,
    genera_recibo boolean DEFAULT true NOT NULL,
    afecta_estado_cuenta boolean DEFAULT true NOT NULL,
    afecta_libre_deuda boolean DEFAULT true NOT NULL,
    id_obligacion_reemplazada bigint,
    id_obligacion_reemplazante bigint,
    motivo_reemplazo text,
    observaciones text,
    CONSTRAINT chk_obligacion_financiera_deleted_at CHECK (((deleted_at IS NULL) OR (deleted_at >= created_at))),
    CONSTRAINT chk_obligacion_financiera_fechas CHECK (((fecha_vencimiento IS NULL) OR (fecha_vencimiento >= fecha_emision))),
    CONSTRAINT chk_obligacion_financiera_periodo CHECK (((periodo_hasta IS NULL) OR (periodo_desde IS NULL) OR (periodo_hasta >= periodo_desde))),
    CONSTRAINT chk_obligacion_estado CHECK (((estado_obligacion)::text = ANY ((ARRAY['PROYECTADA'::character varying, 'EMITIDA'::character varying, 'EXIGIBLE'::character varying, 'PARCIALMENTE_CANCELADA'::character varying, 'CANCELADA'::character varying, 'VENCIDA'::character varying, 'ANULADA'::character varying, 'REEMPLAZADA'::character varying])::text[]))),
    CONSTRAINT chk_obligacion_importes_no_negativos CHECK (((importe_total >= (0)::numeric) AND (saldo_pendiente >= (0)::numeric) AND (importe_cancelado_acumulado >= (0)::numeric) AND (importe_bonificado_acumulado >= (0)::numeric) AND (importe_anulado_acumulado >= (0)::numeric))),
    CONSTRAINT chk_obligacion_saldo_no_supera_total CHECK ((saldo_pendiente <= importe_total))
);


--
-- Name: obligacion_financiera_id_obligacion_financiera_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.obligacion_financiera_id_obligacion_financiera_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: obligacion_financiera_id_obligacion_financiera_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.obligacion_financiera_id_obligacion_financiera_seq OWNED BY public.obligacion_financiera.id_obligacion_financiera;


--
-- Name: obligacion_obligado; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.obligacion_obligado (
    id_obligacion_obligado bigint NOT NULL,
    uid_global uuid DEFAULT gen_random_uuid() NOT NULL,
    version_registro integer DEFAULT 1 NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    deleted_at timestamp without time zone,
    id_instalacion_origen bigint,
    id_instalacion_ultima_modificacion bigint,
    op_id_alta uuid,
    op_id_ultima_modificacion uuid,
    id_obligacion_financiera bigint NOT NULL,
    id_persona bigint NOT NULL,
    rol_obligado character varying(50),
    porcentaje_responsabilidad numeric(5,2)
);


--
-- Name: obligacion_obligado_id_obligacion_obligado_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.obligacion_obligado_id_obligacion_obligado_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: obligacion_obligado_id_obligacion_obligado_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.obligacion_obligado_id_obligacion_obligado_seq OWNED BY public.obligacion_obligado.id_obligacion_obligado;


--
-- Name: ocupacion; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.ocupacion (
    id_ocupacion bigint NOT NULL,
    uid_global uuid DEFAULT gen_random_uuid() NOT NULL,
    version_registro integer DEFAULT 1 NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    deleted_at timestamp without time zone,
    id_instalacion_origen bigint,
    id_instalacion_ultima_modificacion bigint,
    op_id_alta uuid,
    op_id_ultima_modificacion uuid,
    id_inmueble bigint,
    id_unidad_funcional bigint,
    tipo_ocupacion character varying(50) NOT NULL,
    fecha_desde timestamp without time zone NOT NULL,
    fecha_hasta timestamp without time zone,
    descripcion character varying(200),
    observaciones text,
    CONSTRAINT chk_ocupacion_vigencia CHECK (((fecha_hasta IS NULL) OR (fecha_hasta >= fecha_desde))),
    CONSTRAINT chk_ocupacion_xor CHECK ((((id_inmueble IS NOT NULL) AND (id_unidad_funcional IS NULL)) OR ((id_inmueble IS NULL) AND (id_unidad_funcional IS NOT NULL))))
);


--
-- Name: ocupacion_id_ocupacion_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.ocupacion_id_ocupacion_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: ocupacion_id_ocupacion_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.ocupacion_id_ocupacion_seq OWNED BY public.ocupacion.id_ocupacion;


--
-- Name: operacion_auditoria; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.operacion_auditoria (
    id_operacion_auditoria bigint NOT NULL,
    op_id character varying(100),
    nombre_operacion character varying(150) NOT NULL,
    fecha_hora_inicio timestamp without time zone NOT NULL,
    fecha_hora_fin timestamp without time zone,
    estado_operacion character varying(50),
    observaciones text,
    CONSTRAINT chk_operacion_auditoria_periodo CHECK (((fecha_hora_fin IS NULL) OR (fecha_hora_fin >= fecha_hora_inicio)))
);


--
-- Name: operacion_auditoria_id_operacion_auditoria_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.operacion_auditoria_id_operacion_auditoria_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: operacion_auditoria_id_operacion_auditoria_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.operacion_auditoria_id_operacion_auditoria_seq OWNED BY public.operacion_auditoria.id_operacion_auditoria;


--
-- Name: parametro_opcion; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.parametro_opcion (
    id_parametro_opcion bigint NOT NULL,
    id_parametro_sistema bigint NOT NULL,
    codigo_opcion character varying(50) NOT NULL,
    nombre_opcion character varying(150) NOT NULL
);


--
-- Name: parametro_opcion_id_parametro_opcion_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.parametro_opcion_id_parametro_opcion_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: parametro_opcion_id_parametro_opcion_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.parametro_opcion_id_parametro_opcion_seq OWNED BY public.parametro_opcion.id_parametro_opcion;


--
-- Name: parametro_sistema; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.parametro_sistema (
    id_parametro_sistema bigint NOT NULL,
    id_tipo_dato_parametro bigint NOT NULL,
    id_alcance_parametro bigint NOT NULL,
    codigo_parametro character varying(100) NOT NULL,
    nombre_parametro character varying(150) NOT NULL,
    descripcion text
);


--
-- Name: parametro_sistema_id_parametro_sistema_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.parametro_sistema_id_parametro_sistema_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: parametro_sistema_id_parametro_sistema_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.parametro_sistema_id_parametro_sistema_seq OWNED BY public.parametro_sistema.id_parametro_sistema;


--
-- Name: permiso; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.permiso (
    id_permiso bigint NOT NULL,
    codigo_permiso character varying(50) NOT NULL,
    nombre_permiso character varying(150) NOT NULL,
    descripcion text,
    estado_permiso character varying(30) NOT NULL
);


--
-- Name: permiso_id_permiso_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.permiso_id_permiso_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: permiso_id_permiso_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.permiso_id_permiso_seq OWNED BY public.permiso.id_permiso;


--
-- Name: persona; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.persona (
    id_persona bigint NOT NULL,
    uid_global uuid DEFAULT gen_random_uuid() NOT NULL,
    version_registro integer DEFAULT 1 NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    deleted_at timestamp without time zone,
    id_instalacion_origen bigint,
    id_instalacion_ultima_modificacion bigint,
    op_id_alta uuid,
    op_id_ultima_modificacion uuid,
    tipo_persona character varying(50) NOT NULL,
    codigo_persona character varying(50),
    apellido character varying(150),
    nombre character varying(150),
    razon_social character varying(255),
    nombre_fantasia character varying(255),
    estado_persona character varying(50) NOT NULL,
    fecha_nacimiento_constitucion date,
    cuit_cuil character varying(20),
    sexo_genero character varying(50),
    nacionalidad character varying(100),
    fecha_alta timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    fecha_baja timestamp without time zone,
    observaciones text,
    CONSTRAINT chk_persona_deleted_at CHECK (((deleted_at IS NULL) OR (deleted_at >= created_at)))
);


--
-- Name: persona_contacto; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.persona_contacto (
    id_persona_contacto bigint NOT NULL,
    uid_global uuid DEFAULT gen_random_uuid() NOT NULL,
    version_registro integer DEFAULT 1 NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    deleted_at timestamp without time zone,
    id_instalacion_origen bigint,
    id_instalacion_ultima_modificacion bigint,
    op_id_alta uuid,
    op_id_ultima_modificacion uuid,
    id_persona bigint NOT NULL,
    tipo_contacto character varying(50),
    valor_contacto character varying(150) NOT NULL,
    es_principal boolean DEFAULT false NOT NULL,
    fecha_desde date,
    fecha_hasta date,
    observaciones text,
    CONSTRAINT chk_persona_contacto_deleted_at CHECK (((deleted_at IS NULL) OR (deleted_at >= created_at))),
    CONSTRAINT chk_persona_contacto_vigencia CHECK (((fecha_hasta IS NULL) OR (fecha_desde IS NULL) OR (fecha_hasta >= fecha_desde)))
);


--
-- Name: persona_contacto_id_persona_contacto_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.persona_contacto_id_persona_contacto_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: persona_contacto_id_persona_contacto_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.persona_contacto_id_persona_contacto_seq OWNED BY public.persona_contacto.id_persona_contacto;


--
-- Name: persona_documento; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.persona_documento (
    id_persona_documento bigint NOT NULL,
    uid_global uuid DEFAULT gen_random_uuid() NOT NULL,
    version_registro integer DEFAULT 1 NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    deleted_at timestamp without time zone,
    id_instalacion_origen bigint,
    id_instalacion_ultima_modificacion bigint,
    op_id_alta uuid,
    op_id_ultima_modificacion uuid,
    id_persona bigint NOT NULL,
    tipo_documento_persona character varying(50) NOT NULL,
    numero_documento character varying(50) NOT NULL,
    pais_emision character varying(100),
    es_principal boolean DEFAULT false NOT NULL,
    fecha_desde date,
    fecha_hasta date,
    observaciones text,
    CONSTRAINT chk_persona_documento_deleted_at CHECK (((deleted_at IS NULL) OR (deleted_at >= created_at))),
    CONSTRAINT chk_persona_documento_vigencia CHECK (((fecha_hasta IS NULL) OR (fecha_desde IS NULL) OR (fecha_hasta >= fecha_desde)))
);


--
-- Name: persona_documento_id_persona_documento_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.persona_documento_id_persona_documento_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: persona_documento_id_persona_documento_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.persona_documento_id_persona_documento_seq OWNED BY public.persona_documento.id_persona_documento;


--
-- Name: persona_domicilio; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.persona_domicilio (
    id_persona_domicilio bigint NOT NULL,
    uid_global uuid DEFAULT gen_random_uuid() NOT NULL,
    version_registro integer DEFAULT 1 NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    deleted_at timestamp without time zone,
    id_instalacion_origen bigint,
    id_instalacion_ultima_modificacion bigint,
    op_id_alta uuid,
    op_id_ultima_modificacion uuid,
    id_persona bigint NOT NULL,
    tipo_domicilio character varying(50),
    direccion character varying(200),
    localidad character varying(100),
    provincia character varying(100),
    pais character varying(100),
    codigo_postal character varying(20),
    es_principal boolean DEFAULT false NOT NULL,
    fecha_desde date,
    fecha_hasta date,
    observaciones text,
    CONSTRAINT chk_persona_domicilio_deleted_at CHECK (((deleted_at IS NULL) OR (deleted_at >= created_at))),
    CONSTRAINT chk_persona_domicilio_vigencia CHECK (((fecha_hasta IS NULL) OR (fecha_desde IS NULL) OR (fecha_hasta >= fecha_desde)))
);


--
-- Name: persona_domicilio_id_persona_domicilio_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.persona_domicilio_id_persona_domicilio_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: persona_domicilio_id_persona_domicilio_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.persona_domicilio_id_persona_domicilio_seq OWNED BY public.persona_domicilio.id_persona_domicilio;


--
-- Name: persona_id_persona_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.persona_id_persona_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: persona_id_persona_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.persona_id_persona_seq OWNED BY public.persona.id_persona;


--
-- Name: persona_relacion; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.persona_relacion (
    id_persona_relacion bigint NOT NULL,
    uid_global uuid DEFAULT gen_random_uuid() NOT NULL,
    version_registro integer DEFAULT 1 NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    deleted_at timestamp without time zone,
    id_instalacion_origen bigint,
    id_instalacion_ultima_modificacion bigint,
    op_id_alta uuid,
    op_id_ultima_modificacion uuid,
    id_persona_origen bigint NOT NULL,
    id_persona_destino bigint NOT NULL,
    tipo_relacion character varying(50) NOT NULL,
    fecha_desde timestamp without time zone NOT NULL,
    fecha_hasta timestamp without time zone,
    observaciones text,
    CONSTRAINT chk_persona_relacion_no_autorreferencia CHECK ((id_persona_origen <> id_persona_destino)),
    CONSTRAINT chk_persona_relacion_vigencia CHECK (((fecha_hasta IS NULL) OR (fecha_hasta >= fecha_desde)))
);


--
-- Name: persona_relacion_id_persona_relacion_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.persona_relacion_id_persona_relacion_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: persona_relacion_id_persona_relacion_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.persona_relacion_id_persona_relacion_seq OWNED BY public.persona_relacion.id_persona_relacion;


--
-- Name: relacion_generadora; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.relacion_generadora (
    id_relacion_generadora bigint NOT NULL,
    uid_global uuid DEFAULT gen_random_uuid() NOT NULL,
    version_registro integer DEFAULT 1 NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    deleted_at timestamp without time zone,
    id_instalacion_origen bigint,
    id_instalacion_ultima_modificacion bigint,
    op_id_alta uuid,
    op_id_ultima_modificacion uuid,
    tipo_origen character varying(50) NOT NULL,
    id_origen bigint NOT NULL,
    descripcion text,
    fecha_alta timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    estado_relacion_generadora character varying(30) DEFAULT 'BORRADOR'::character varying NOT NULL,
    CONSTRAINT chk_relacion_generadora_estado CHECK (((estado_relacion_generadora)::text = ANY ((ARRAY['BORRADOR'::character varying, 'ACTIVA'::character varying, 'CANCELADA'::character varying, 'FINALIZADA'::character varying])::text[])))
);


--
-- Name: relacion_generadora_id_relacion_generadora_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.relacion_generadora_id_relacion_generadora_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: relacion_generadora_id_relacion_generadora_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.relacion_generadora_id_relacion_generadora_seq OWNED BY public.relacion_generadora.id_relacion_generadora;


--
-- Name: relacion_persona_rol; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.relacion_persona_rol (
    id_relacion_persona_rol bigint NOT NULL,
    uid_global uuid DEFAULT gen_random_uuid() NOT NULL,
    version_registro integer DEFAULT 1 NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    deleted_at timestamp without time zone,
    id_instalacion_origen bigint,
    id_instalacion_ultima_modificacion bigint,
    op_id_alta uuid,
    op_id_ultima_modificacion uuid,
    id_persona bigint NOT NULL,
    id_rol_participacion bigint NOT NULL,
    tipo_relacion character varying(50) NOT NULL,
    id_relacion bigint NOT NULL,
    fecha_desde timestamp without time zone NOT NULL,
    fecha_hasta timestamp without time zone,
    observaciones text,
    CONSTRAINT chk_relacion_persona_rol_vigencia CHECK (((fecha_hasta IS NULL) OR (fecha_hasta >= fecha_desde)))
);


--
-- Name: relacion_persona_rol_id_relacion_persona_rol_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.relacion_persona_rol_id_relacion_persona_rol_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: relacion_persona_rol_id_relacion_persona_rol_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.relacion_persona_rol_id_relacion_persona_rol_seq OWNED BY public.relacion_persona_rol.id_relacion_persona_rol;


--
-- Name: representacion_poder; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.representacion_poder (
    id_representacion_poder bigint NOT NULL,
    uid_global uuid DEFAULT gen_random_uuid() NOT NULL,
    version_registro integer DEFAULT 1 NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    deleted_at timestamp without time zone,
    id_instalacion_origen bigint,
    id_instalacion_ultima_modificacion bigint,
    op_id_alta uuid,
    op_id_ultima_modificacion uuid,
    id_persona_representado bigint NOT NULL,
    id_persona_representante bigint NOT NULL,
    tipo_poder character varying(50),
    estado_representacion character varying(50),
    fecha_desde timestamp without time zone NOT NULL,
    fecha_hasta timestamp without time zone,
    descripcion text,
    CONSTRAINT chk_representacion_poder_no_autorreferencia CHECK ((id_persona_representado <> id_persona_representante)),
    CONSTRAINT chk_representacion_poder_vigencia CHECK (((fecha_hasta IS NULL) OR (fecha_hasta >= fecha_desde)))
);


--
-- Name: representacion_poder_id_representacion_poder_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.representacion_poder_id_representacion_poder_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: representacion_poder_id_representacion_poder_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.representacion_poder_id_representacion_poder_seq OWNED BY public.representacion_poder.id_representacion_poder;


--
-- Name: rescision_finalizacion_alquiler; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.rescision_finalizacion_alquiler (
    id_rescision_locativa bigint NOT NULL,
    uid_global uuid DEFAULT gen_random_uuid() NOT NULL,
    version_registro integer DEFAULT 1 NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    deleted_at timestamp without time zone,
    id_instalacion_origen bigint,
    id_instalacion_ultima_modificacion bigint,
    op_id_alta uuid,
    op_id_ultima_modificacion uuid,
    id_contrato_alquiler bigint NOT NULL,
    fecha_rescision date NOT NULL,
    motivo character varying(200),
    observaciones text
);


--
-- Name: rescision_finalizacion_alquiler_id_rescision_locativa_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.rescision_finalizacion_alquiler_id_rescision_locativa_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: rescision_finalizacion_alquiler_id_rescision_locativa_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.rescision_finalizacion_alquiler_id_rescision_locativa_seq OWNED BY public.rescision_finalizacion_alquiler.id_rescision_locativa;


--
-- Name: rescision_venta; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.rescision_venta (
    id_rescision_venta bigint NOT NULL,
    uid_global uuid DEFAULT gen_random_uuid() NOT NULL,
    version_registro integer DEFAULT 1 NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    deleted_at timestamp without time zone,
    id_instalacion_origen bigint,
    id_instalacion_ultima_modificacion bigint,
    op_id_alta uuid,
    op_id_ultima_modificacion uuid,
    id_venta bigint NOT NULL,
    fecha_rescision timestamp without time zone NOT NULL,
    motivo character varying(200),
    observaciones text
);


--
-- Name: rescision_venta_id_rescision_venta_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.rescision_venta_id_rescision_venta_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: rescision_venta_id_rescision_venta_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.rescision_venta_id_rescision_venta_seq OWNED BY public.rescision_venta.id_rescision_venta;


--
-- Name: reserva_locativa; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.reserva_locativa (
    id_reserva_locativa bigint NOT NULL,
    uid_global uuid DEFAULT gen_random_uuid() NOT NULL,
    version_registro integer DEFAULT 1 NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    deleted_at timestamp without time zone,
    id_instalacion_origen bigint,
    id_instalacion_ultima_modificacion bigint,
    op_id_alta uuid,
    op_id_ultima_modificacion uuid,
    id_solicitud_alquiler bigint,
    codigo_reserva character varying(50) NOT NULL,
    fecha_reserva timestamp without time zone NOT NULL,
    fecha_vencimiento timestamp without time zone,
    estado_reserva character varying(30) NOT NULL,
    observaciones text,
    CONSTRAINT chk_reserva_locativa_vencimiento CHECK (((fecha_vencimiento IS NULL) OR (fecha_vencimiento >= fecha_reserva)))
);


--
-- Name: reserva_locativa_id_reserva_locativa_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.reserva_locativa_id_reserva_locativa_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: reserva_locativa_id_reserva_locativa_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.reserva_locativa_id_reserva_locativa_seq OWNED BY public.reserva_locativa.id_reserva_locativa;


--
-- Name: reserva_venta; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.reserva_venta (
    id_reserva_venta bigint NOT NULL,
    uid_global uuid DEFAULT gen_random_uuid() NOT NULL,
    version_registro integer DEFAULT 1 NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    deleted_at timestamp without time zone,
    id_instalacion_origen bigint,
    id_instalacion_ultima_modificacion bigint,
    op_id_alta uuid,
    op_id_ultima_modificacion uuid,
    codigo_reserva character varying(50) NOT NULL,
    fecha_reserva timestamp without time zone NOT NULL,
    estado_reserva character varying(30) NOT NULL,
    fecha_vencimiento timestamp without time zone,
    observaciones text,
    CONSTRAINT chk_reserva_venta_vencimiento CHECK (((fecha_vencimiento IS NULL) OR (fecha_vencimiento >= fecha_reserva)))
);


--
-- Name: reserva_venta_id_reserva_venta_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.reserva_venta_id_reserva_venta_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: reserva_venta_id_reserva_venta_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.reserva_venta_id_reserva_venta_seq OWNED BY public.reserva_venta.id_reserva_venta;


--
-- Name: resultado_evento_auditoria; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.resultado_evento_auditoria (
    id_resultado_evento_auditoria bigint CONSTRAINT resultado_evento_auditoria_id_resultado_evento_auditor_not_null NOT NULL,
    codigo_resultado character varying(50) NOT NULL,
    nombre_resultado character varying(150) NOT NULL,
    descripcion text
);


--
-- Name: resultado_evento_auditoria_id_resultado_evento_auditoria_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.resultado_evento_auditoria_id_resultado_evento_auditoria_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: resultado_evento_auditoria_id_resultado_evento_auditoria_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.resultado_evento_auditoria_id_resultado_evento_auditoria_seq OWNED BY public.resultado_evento_auditoria.id_resultado_evento_auditoria;


--
-- Name: rol_participacion; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.rol_participacion (
    id_rol_participacion bigint NOT NULL,
    uid_global uuid DEFAULT gen_random_uuid() NOT NULL,
    version_registro integer DEFAULT 1 NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    deleted_at timestamp without time zone,
    id_instalacion_origen bigint,
    id_instalacion_ultima_modificacion bigint,
    op_id_alta uuid,
    op_id_ultima_modificacion uuid,
    codigo_rol character varying(50) NOT NULL,
    nombre_rol character varying(150) NOT NULL,
    descripcion text,
    estado_rol character varying(30) NOT NULL
);


--
-- Name: rol_participacion_id_rol_participacion_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.rol_participacion_id_rol_participacion_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: rol_participacion_id_rol_participacion_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.rol_participacion_id_rol_participacion_seq OWNED BY public.rol_participacion.id_rol_participacion;


--
-- Name: rol_seguridad; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.rol_seguridad (
    id_rol_seguridad bigint NOT NULL,
    codigo_rol character varying(50) NOT NULL,
    nombre_rol character varying(150) NOT NULL,
    descripcion text,
    estado_rol character varying(30) NOT NULL
);


--
-- Name: rol_seguridad_id_rol_seguridad_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.rol_seguridad_id_rol_seguridad_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: rol_seguridad_id_rol_seguridad_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.rol_seguridad_id_rol_seguridad_seq OWNED BY public.rol_seguridad.id_rol_seguridad;


--
-- Name: rol_seguridad_permiso; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.rol_seguridad_permiso (
    id_rol_seguridad_permiso bigint NOT NULL,
    id_rol_seguridad bigint NOT NULL,
    id_permiso bigint NOT NULL
);


--
-- Name: rol_seguridad_permiso_id_rol_seguridad_permiso_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.rol_seguridad_permiso_id_rol_seguridad_permiso_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: rol_seguridad_permiso_id_rol_seguridad_permiso_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.rol_seguridad_permiso_id_rol_seguridad_permiso_seq OWNED BY public.rol_seguridad_permiso.id_rol_seguridad_permiso;


--
-- Name: seccion_configuracion; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.seccion_configuracion (
    id_seccion_configuracion bigint NOT NULL,
    codigo_seccion character varying(50) NOT NULL,
    nombre_seccion character varying(150) NOT NULL,
    descripcion text
);


--
-- Name: seccion_configuracion_id_seccion_configuracion_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.seccion_configuracion_id_seccion_configuracion_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: seccion_configuracion_id_seccion_configuracion_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.seccion_configuracion_id_seccion_configuracion_seq OWNED BY public.seccion_configuracion.id_seccion_configuracion;


--
-- Name: servicio; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.servicio (
    id_servicio bigint NOT NULL,
    uid_global uuid DEFAULT gen_random_uuid() NOT NULL,
    version_registro integer DEFAULT 1 NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    deleted_at timestamp without time zone,
    id_instalacion_origen bigint,
    id_instalacion_ultima_modificacion bigint,
    op_id_alta uuid,
    op_id_ultima_modificacion uuid,
    codigo_servicio character varying(50) NOT NULL,
    nombre_servicio character varying(150) NOT NULL,
    descripcion text,
    estado_servicio character varying(30) NOT NULL
);


--
-- Name: servicio_id_servicio_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.servicio_id_servicio_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: servicio_id_servicio_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.servicio_id_servicio_seq OWNED BY public.servicio.id_servicio;


--
-- Name: sesion_usuario; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.sesion_usuario (
    id_sesion_usuario bigint NOT NULL,
    id_usuario bigint NOT NULL,
    id_credencial_usuario bigint,
    id_sucursal_operativa bigint,
    id_instalacion_origen bigint NOT NULL,
    token_sesion character varying(200) NOT NULL,
    fecha_hora_inicio timestamp without time zone NOT NULL,
    fecha_hora_ultima_actividad timestamp without time zone,
    fecha_hora_cierre timestamp without time zone,
    estado_sesion character varying(30) NOT NULL,
    motivo_cierre text,
    origen_autenticacion character varying(50),
    ip_origen character varying(50),
    nombre_equipo_origen character varying(150),
    version_cliente character varying(100),
    requiere_reautenticacion boolean DEFAULT false NOT NULL,
    expira_en timestamp without time zone,
    observaciones text,
    CONSTRAINT chk_sesion_usuario_periodo CHECK (((fecha_hora_cierre IS NULL) OR (fecha_hora_cierre >= fecha_hora_inicio)))
);


--
-- Name: sesion_usuario_id_sesion_usuario_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.sesion_usuario_id_sesion_usuario_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: sesion_usuario_id_sesion_usuario_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.sesion_usuario_id_sesion_usuario_seq OWNED BY public.sesion_usuario.id_sesion_usuario;


--
-- Name: sincronizacion_operacion; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.sincronizacion_operacion (
    id_sincronizacion_operacion bigint NOT NULL,
    id_sincronizacion_paquete bigint NOT NULL,
    op_id character varying(100) NOT NULL,
    tipo_operacion character varying(50) NOT NULL,
    entidad_principal character varying(100) NOT NULL,
    uid_entidad uuid,
    id_entidad_principal bigint,
    version_registro integer,
    estado_operacion character varying(50) NOT NULL,
    fecha_hora_operacion timestamp without time zone NOT NULL,
    orden_en_paquete integer NOT NULL,
    payload_operacion jsonb,
    hash_operacion character varying(255),
    requiere_resolucion_manual boolean DEFAULT false NOT NULL,
    observaciones text,
    CONSTRAINT chk_sync_op_version_registro CHECK (((version_registro IS NULL) OR (version_registro >= 1))),
    CONSTRAINT chk_sync_operacion_orden CHECK ((orden_en_paquete > 0))
);


--
-- Name: sincronizacion_operacion_id_sincronizacion_operacion_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.sincronizacion_operacion_id_sincronizacion_operacion_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: sincronizacion_operacion_id_sincronizacion_operacion_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.sincronizacion_operacion_id_sincronizacion_operacion_seq OWNED BY public.sincronizacion_operacion.id_sincronizacion_operacion;


--
-- Name: sincronizacion_paquete; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.sincronizacion_paquete (
    id_sincronizacion_paquete bigint NOT NULL,
    id_instalacion_origen bigint NOT NULL,
    codigo_paquete character varying(100) NOT NULL,
    estado_paquete character varying(50) NOT NULL,
    fecha_hora_generacion timestamp without time zone NOT NULL,
    fecha_hora_envio timestamp without time zone,
    fecha_hora_cierre timestamp without time zone,
    cantidad_operaciones integer DEFAULT 0 NOT NULL,
    hash_paquete character varying(255),
    observaciones text,
    CONSTRAINT chk_sync_paquete_cantidad_operaciones CHECK ((cantidad_operaciones >= 0))
);


--
-- Name: sincronizacion_paquete_id_sincronizacion_paquete_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.sincronizacion_paquete_id_sincronizacion_paquete_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: sincronizacion_paquete_id_sincronizacion_paquete_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.sincronizacion_paquete_id_sincronizacion_paquete_seq OWNED BY public.sincronizacion_paquete.id_sincronizacion_paquete;


--
-- Name: sincronizacion_recepcion; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.sincronizacion_recepcion (
    id_sincronizacion_recepcion bigint NOT NULL,
    op_id character varying(100) NOT NULL,
    id_instalacion_origen bigint,
    id_instalacion_receptora bigint NOT NULL,
    uid_entidad uuid,
    tipo_entidad character varying(100),
    tipo_evento character varying(50),
    version_registro integer,
    payload_operacion jsonb,
    hash_payload character varying(255),
    fecha_hora_recepcion timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    fecha_hora_procesamiento timestamp without time zone,
    estado_recepcion character varying(50) NOT NULL,
    id_conflicto_sincronizacion bigint,
    detalle text,
    CONSTRAINT chk_sync_recepcion_version_registro CHECK (((version_registro IS NULL) OR (version_registro >= 1)))
);


--
-- Name: sincronizacion_recepcion_id_sincronizacion_recepcion_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.sincronizacion_recepcion_id_sincronizacion_recepcion_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: sincronizacion_recepcion_id_sincronizacion_recepcion_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.sincronizacion_recepcion_id_sincronizacion_recepcion_seq OWNED BY public.sincronizacion_recepcion.id_sincronizacion_recepcion;


--
-- Name: solicitud_alquiler; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.solicitud_alquiler (
    id_solicitud_alquiler bigint NOT NULL,
    uid_global uuid DEFAULT gen_random_uuid() NOT NULL,
    version_registro integer DEFAULT 1 NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    deleted_at timestamp without time zone,
    id_instalacion_origen bigint,
    id_instalacion_ultima_modificacion bigint,
    op_id_alta uuid,
    op_id_ultima_modificacion uuid,
    codigo_solicitud character varying(50) NOT NULL,
    fecha_solicitud timestamp without time zone NOT NULL,
    estado_solicitud character varying(30) NOT NULL,
    observaciones text
);


--
-- Name: solicitud_alquiler_id_solicitud_alquiler_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.solicitud_alquiler_id_solicitud_alquiler_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: solicitud_alquiler_id_solicitud_alquiler_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.solicitud_alquiler_id_solicitud_alquiler_seq OWNED BY public.solicitud_alquiler.id_solicitud_alquiler;


--
-- Name: sucursal; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.sucursal (
    id_sucursal bigint NOT NULL,
    uid_global uuid DEFAULT gen_random_uuid() NOT NULL,
    version_registro integer DEFAULT 1 NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    deleted_at timestamp without time zone,
    id_instalacion_origen bigint,
    id_instalacion_ultima_modificacion bigint,
    op_id_alta uuid,
    op_id_ultima_modificacion uuid,
    codigo_sucursal character varying(50) NOT NULL,
    nombre_sucursal character varying(150) NOT NULL,
    descripcion_sucursal text,
    estado_sucursal character varying(30) NOT NULL,
    es_casa_central boolean DEFAULT false NOT NULL,
    permite_operacion boolean DEFAULT true NOT NULL,
    fecha_alta timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    fecha_baja timestamp without time zone,
    observaciones text,
    CONSTRAINT chk_sucursal_deleted_at CHECK (((deleted_at IS NULL) OR (deleted_at >= created_at)))
);


--
-- Name: sucursal_id_sucursal_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.sucursal_id_sucursal_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: sucursal_id_sucursal_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.sucursal_id_sucursal_seq OWNED BY public.sucursal.id_sucursal;


--
-- Name: tipo_dato_parametro; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tipo_dato_parametro (
    id_tipo_dato_parametro bigint NOT NULL,
    codigo_tipo_dato character varying(50) NOT NULL,
    nombre_tipo_dato character varying(150) NOT NULL
);


--
-- Name: tipo_dato_parametro_id_tipo_dato_parametro_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.tipo_dato_parametro_id_tipo_dato_parametro_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: tipo_dato_parametro_id_tipo_dato_parametro_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.tipo_dato_parametro_id_tipo_dato_parametro_seq OWNED BY public.tipo_dato_parametro.id_tipo_dato_parametro;


--
-- Name: tipo_documental; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tipo_documental (
    id_tipo_documental bigint NOT NULL,
    uid_global uuid DEFAULT gen_random_uuid() NOT NULL,
    version_registro integer DEFAULT 1 NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    deleted_at timestamp without time zone,
    id_instalacion_origen bigint,
    id_instalacion_ultima_modificacion bigint,
    op_id_alta uuid,
    op_id_ultima_modificacion uuid,
    codigo_tipo_documental character varying(50) NOT NULL,
    nombre_tipo_documental character varying(150) NOT NULL,
    descripcion text,
    admite_versionado boolean DEFAULT true NOT NULL,
    requiere_archivo boolean DEFAULT true NOT NULL,
    requiere_numeracion boolean DEFAULT false NOT NULL,
    estado_tipo_documental character varying(30) NOT NULL
);


--
-- Name: tipo_documental_id_tipo_documental_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.tipo_documental_id_tipo_documental_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: tipo_documental_id_tipo_documental_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.tipo_documental_id_tipo_documental_seq OWNED BY public.tipo_documental.id_tipo_documental;


--
-- Name: tipo_evento_auditoria; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tipo_evento_auditoria (
    id_tipo_evento_auditoria bigint NOT NULL,
    codigo_tipo_evento character varying(50) NOT NULL,
    nombre_tipo_evento character varying(150) NOT NULL,
    descripcion text
);


--
-- Name: tipo_evento_auditoria_id_tipo_evento_auditoria_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.tipo_evento_auditoria_id_tipo_evento_auditoria_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: tipo_evento_auditoria_id_tipo_evento_auditoria_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.tipo_evento_auditoria_id_tipo_evento_auditoria_seq OWNED BY public.tipo_evento_auditoria.id_tipo_evento_auditoria;


--
-- Name: unidad_funcional; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.unidad_funcional (
    id_unidad_funcional bigint NOT NULL,
    uid_global uuid DEFAULT gen_random_uuid() NOT NULL,
    version_registro integer DEFAULT 1 NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    deleted_at timestamp without time zone,
    id_instalacion_origen bigint,
    id_instalacion_ultima_modificacion bigint,
    op_id_alta uuid,
    op_id_ultima_modificacion uuid,
    id_inmueble bigint NOT NULL,
    codigo_unidad character varying(50) NOT NULL,
    nombre_unidad character varying(150),
    superficie numeric(14,2),
    estado_administrativo character varying(30) NOT NULL,
    estado_operativo character varying(30) NOT NULL,
    fecha_alta timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    fecha_baja timestamp without time zone,
    observaciones text
);


--
-- Name: unidad_funcional_id_unidad_funcional_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.unidad_funcional_id_unidad_funcional_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: unidad_funcional_id_unidad_funcional_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.unidad_funcional_id_unidad_funcional_seq OWNED BY public.unidad_funcional.id_unidad_funcional;


--
-- Name: unidad_funcional_servicio; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.unidad_funcional_servicio (
    id_unidad_funcional_servicio bigint NOT NULL,
    uid_global uuid DEFAULT gen_random_uuid() NOT NULL,
    version_registro integer DEFAULT 1 NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    deleted_at timestamp without time zone,
    id_instalacion_origen bigint,
    id_instalacion_ultima_modificacion bigint,
    op_id_alta uuid,
    op_id_ultima_modificacion uuid,
    id_unidad_funcional bigint NOT NULL,
    id_servicio bigint NOT NULL,
    estado character varying(30),
    fecha_alta timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: unidad_funcional_servicio_id_unidad_funcional_servicio_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.unidad_funcional_servicio_id_unidad_funcional_servicio_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: unidad_funcional_servicio_id_unidad_funcional_servicio_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.unidad_funcional_servicio_id_unidad_funcional_servicio_seq OWNED BY public.unidad_funcional_servicio.id_unidad_funcional_servicio;


--
-- Name: usuario; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.usuario (
    id_usuario bigint NOT NULL,
    codigo_usuario character varying(50) NOT NULL,
    login character varying(100) NOT NULL,
    email character varying(150),
    estado_usuario character varying(30) NOT NULL,
    fecha_alta timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    fecha_baja timestamp without time zone,
    fecha_ultimo_acceso timestamp without time zone,
    usuario_sistema_interno boolean DEFAULT false NOT NULL,
    observaciones text
);


--
-- Name: usuario_id_usuario_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.usuario_id_usuario_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: usuario_id_usuario_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.usuario_id_usuario_seq OWNED BY public.usuario.id_usuario;


--
-- Name: usuario_persona; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.usuario_persona (
    id_usuario_persona bigint NOT NULL,
    id_usuario bigint NOT NULL,
    id_persona bigint NOT NULL,
    tipo_vinculo_usuario_persona character varying(50),
    es_vinculo_principal boolean DEFAULT false NOT NULL,
    fecha_desde timestamp without time zone NOT NULL,
    fecha_hasta timestamp without time zone,
    motivo_vinculo text,
    observaciones text,
    CONSTRAINT chk_usuario_persona_vigencia CHECK (((fecha_hasta IS NULL) OR (fecha_hasta >= fecha_desde)))
);


--
-- Name: usuario_persona_id_usuario_persona_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.usuario_persona_id_usuario_persona_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: usuario_persona_id_usuario_persona_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.usuario_persona_id_usuario_persona_seq OWNED BY public.usuario_persona.id_usuario_persona;


--
-- Name: usuario_rol_seguridad; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.usuario_rol_seguridad (
    id_usuario_rol_seguridad bigint NOT NULL,
    id_usuario bigint NOT NULL,
    id_rol_seguridad bigint NOT NULL,
    fecha_desde timestamp without time zone NOT NULL,
    fecha_hasta timestamp without time zone,
    CONSTRAINT chk_usuario_rol_seguridad_vigencia CHECK (((fecha_hasta IS NULL) OR (fecha_hasta >= fecha_desde)))
);


--
-- Name: usuario_rol_seguridad_id_usuario_rol_seguridad_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.usuario_rol_seguridad_id_usuario_rol_seguridad_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: usuario_rol_seguridad_id_usuario_rol_seguridad_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.usuario_rol_seguridad_id_usuario_rol_seguridad_seq OWNED BY public.usuario_rol_seguridad.id_usuario_rol_seguridad;


--
-- Name: usuario_rol_sucursal; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.usuario_rol_sucursal (
    id_usuario_rol_sucursal bigint NOT NULL,
    id_usuario bigint NOT NULL,
    id_rol_seguridad bigint NOT NULL,
    id_sucursal bigint NOT NULL,
    fecha_desde timestamp without time zone NOT NULL,
    fecha_hasta timestamp without time zone,
    CONSTRAINT chk_usuario_rol_sucursal_vigencia CHECK (((fecha_hasta IS NULL) OR (fecha_hasta >= fecha_desde)))
);


--
-- Name: usuario_rol_sucursal_id_usuario_rol_sucursal_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.usuario_rol_sucursal_id_usuario_rol_sucursal_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: usuario_rol_sucursal_id_usuario_rol_sucursal_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.usuario_rol_sucursal_id_usuario_rol_sucursal_seq OWNED BY public.usuario_rol_sucursal.id_usuario_rol_sucursal;


--
-- Name: usuario_sucursal; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.usuario_sucursal (
    id_usuario_sucursal bigint NOT NULL,
    id_usuario bigint NOT NULL,
    id_sucursal bigint NOT NULL,
    tipo_habilitacion_sucursal character varying(50),
    es_sucursal_predeterminada boolean DEFAULT false NOT NULL,
    puede_operar boolean DEFAULT true NOT NULL,
    puede_consultar boolean DEFAULT true NOT NULL,
    puede_administrar boolean DEFAULT false NOT NULL,
    fecha_desde timestamp without time zone NOT NULL,
    fecha_hasta timestamp without time zone,
    estado_vinculo character varying(30) NOT NULL,
    observaciones text,
    CONSTRAINT chk_usuario_sucursal_vigencia CHECK (((fecha_hasta IS NULL) OR (fecha_hasta >= fecha_desde)))
);


--
-- Name: usuario_sucursal_id_usuario_sucursal_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.usuario_sucursal_id_usuario_sucursal_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: usuario_sucursal_id_usuario_sucursal_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.usuario_sucursal_id_usuario_sucursal_seq OWNED BY public.usuario_sucursal.id_usuario_sucursal;


--
-- Name: valor_parametro; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.valor_parametro (
    id_valor_parametro bigint NOT NULL,
    id_parametro_sistema bigint NOT NULL,
    id_sucursal bigint,
    id_instalacion bigint,
    valor_parametro text,
    es_valor_vigente boolean DEFAULT true NOT NULL,
    fecha_desde timestamp without time zone,
    fecha_hasta timestamp without time zone,
    CONSTRAINT chk_valor_parametro_vigencia CHECK (((fecha_hasta IS NULL) OR (fecha_desde IS NULL) OR (fecha_hasta >= fecha_desde)))
);


--
-- Name: valor_parametro_id_valor_parametro_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.valor_parametro_id_valor_parametro_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: valor_parametro_id_valor_parametro_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.valor_parametro_id_valor_parametro_seq OWNED BY public.valor_parametro.id_valor_parametro;


--
-- Name: venta; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.venta (
    id_venta bigint NOT NULL,
    uid_global uuid DEFAULT gen_random_uuid() NOT NULL,
    version_registro integer DEFAULT 1 NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    deleted_at timestamp without time zone,
    id_instalacion_origen bigint,
    id_instalacion_ultima_modificacion bigint,
    op_id_alta uuid,
    op_id_ultima_modificacion uuid,
    id_reserva_venta bigint,
    codigo_venta character varying(50) NOT NULL,
    fecha_venta timestamp without time zone NOT NULL,
    estado_venta character varying(30) NOT NULL,
    monto_total numeric(14,2),
    observaciones text
);


--
-- Name: venta_id_venta_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.venta_id_venta_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: venta_id_venta_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.venta_id_venta_seq OWNED BY public.venta.id_venta;


--
-- Name: venta_objeto_inmobiliario; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.venta_objeto_inmobiliario (
    id_venta_objeto bigint NOT NULL,
    uid_global uuid DEFAULT gen_random_uuid() NOT NULL,
    version_registro integer DEFAULT 1 NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    deleted_at timestamp without time zone,
    id_instalacion_origen bigint,
    id_instalacion_ultima_modificacion bigint,
    op_id_alta uuid,
    op_id_ultima_modificacion uuid,
    id_venta bigint NOT NULL,
    id_inmueble bigint,
    id_unidad_funcional bigint,
    precio_asignado numeric(14,2),
    observaciones text,
    CONSTRAINT chk_vo_xor CHECK ((((id_inmueble IS NOT NULL) AND (id_unidad_funcional IS NULL)) OR ((id_inmueble IS NULL) AND (id_unidad_funcional IS NOT NULL))))
);


--
-- Name: venta_objeto_inmobiliario_id_venta_objeto_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.venta_objeto_inmobiliario_id_venta_objeto_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: venta_objeto_inmobiliario_id_venta_objeto_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.venta_objeto_inmobiliario_id_venta_objeto_seq OWNED BY public.venta_objeto_inmobiliario.id_venta_objeto;


--
-- Name: ajuste_alquiler id_ajuste_alquiler; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ajuste_alquiler ALTER COLUMN id_ajuste_alquiler SET DEFAULT nextval('public.ajuste_alquiler_id_ajuste_alquiler_seq'::regclass);


--
-- Name: alcance_autorizacion id_alcance_autorizacion; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alcance_autorizacion ALTER COLUMN id_alcance_autorizacion SET DEFAULT nextval('public.alcance_autorizacion_id_alcance_autorizacion_seq'::regclass);


--
-- Name: alcance_parametro id_alcance_parametro; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alcance_parametro ALTER COLUMN id_alcance_parametro SET DEFAULT nextval('public.alcance_parametro_id_alcance_parametro_seq'::regclass);


--
-- Name: aplicacion_financiera id_aplicacion_financiera; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.aplicacion_financiera ALTER COLUMN id_aplicacion_financiera SET DEFAULT nextval('public.aplicacion_financiera_id_aplicacion_financiera_seq'::regclass);


--
-- Name: archivo_digital id_archivo_digital; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.archivo_digital ALTER COLUMN id_archivo_digital SET DEFAULT nextval('public.archivo_digital_id_archivo_digital_seq'::regclass);


--
-- Name: cartera_locativa id_cartera_locativa; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.cartera_locativa ALTER COLUMN id_cartera_locativa SET DEFAULT nextval('public.cartera_locativa_id_cartera_locativa_seq'::regclass);


--
-- Name: catalogo_maestro id_catalogo_maestro; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.catalogo_maestro ALTER COLUMN id_catalogo_maestro SET DEFAULT nextval('public.catalogo_maestro_id_catalogo_maestro_seq'::regclass);


--
-- Name: cesion id_cesion; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.cesion ALTER COLUMN id_cesion SET DEFAULT nextval('public.cesion_id_cesion_seq'::regclass);


--
-- Name: outbox_event id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.outbox_event ALTER COLUMN id SET DEFAULT nextval('public.outbox_event_id_seq'::regclass);


--
-- Name: cliente_comprador id_cliente_comprador; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.cliente_comprador ALTER COLUMN id_cliente_comprador SET DEFAULT nextval('public.cliente_comprador_id_cliente_comprador_seq'::regclass);


--
-- Name: composicion_obligacion id_composicion_obligacion; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.composicion_obligacion ALTER COLUMN id_composicion_obligacion SET DEFAULT nextval('public.composicion_obligacion_id_composicion_obligacion_seq'::regclass);


--
-- Name: concepto_financiero id_concepto_financiero; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.concepto_financiero ALTER COLUMN id_concepto_financiero SET DEFAULT nextval('public.concepto_financiero_id_concepto_financiero_seq'::regclass);


--
-- Name: conciliacion_bancaria id_conciliacion_bancaria; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.conciliacion_bancaria ALTER COLUMN id_conciliacion_bancaria SET DEFAULT nextval('public.conciliacion_bancaria_id_conciliacion_bancaria_seq'::regclass);


--
-- Name: condicion_economica_alquiler id_condicion_economica; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.condicion_economica_alquiler ALTER COLUMN id_condicion_economica SET DEFAULT nextval('public.condicion_economica_alquiler_id_condicion_economica_seq'::regclass);


--
-- Name: configuracion_general id_configuracion_general; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.configuracion_general ALTER COLUMN id_configuracion_general SET DEFAULT nextval('public.configuracion_general_id_configuracion_general_seq'::regclass);


--
-- Name: conflicto_sincronizacion id_conflicto_sincronizacion; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.conflicto_sincronizacion ALTER COLUMN id_conflicto_sincronizacion SET DEFAULT nextval('public.conflicto_sincronizacion_id_conflicto_sincronizacion_seq'::regclass);


--
-- Name: contrato_alquiler id_contrato_alquiler; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contrato_alquiler ALTER COLUMN id_contrato_alquiler SET DEFAULT nextval('public.contrato_alquiler_id_contrato_alquiler_seq'::regclass);


--
-- Name: contrato_objeto_locativo id_contrato_objeto; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contrato_objeto_locativo ALTER COLUMN id_contrato_objeto SET DEFAULT nextval('public.contrato_objeto_locativo_id_contrato_objeto_seq'::regclass);


--
-- Name: credencial_usuario id_credencial_usuario; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.credencial_usuario ALTER COLUMN id_credencial_usuario SET DEFAULT nextval('public.credencial_usuario_id_credencial_usuario_seq'::regclass);


--
-- Name: cuenta_financiera id_cuenta_financiera; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.cuenta_financiera ALTER COLUMN id_cuenta_financiera SET DEFAULT nextval('public.cuenta_financiera_id_cuenta_financiera_seq'::regclass);


--
-- Name: denegacion_explicita id_denegacion_explicita; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.denegacion_explicita ALTER COLUMN id_denegacion_explicita SET DEFAULT nextval('public.denegacion_explicita_id_denegacion_explicita_seq'::regclass);


--
-- Name: desarrollo id_desarrollo; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.desarrollo ALTER COLUMN id_desarrollo SET DEFAULT nextval('public.desarrollo_id_desarrollo_seq'::regclass);


--
-- Name: desarrollo_sucursal id_desarrollo_sucursal; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.desarrollo_sucursal ALTER COLUMN id_desarrollo_sucursal SET DEFAULT nextval('public.desarrollo_sucursal_id_desarrollo_sucursal_seq'::regclass);


--
-- Name: detalle_cambio_auditoria id_detalle_cambio_auditoria; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.detalle_cambio_auditoria ALTER COLUMN id_detalle_cambio_auditoria SET DEFAULT nextval('public.detalle_cambio_auditoria_id_detalle_cambio_auditoria_seq'::regclass);


--
-- Name: detalle_conciliacion id_detalle_conciliacion; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.detalle_conciliacion ALTER COLUMN id_detalle_conciliacion SET DEFAULT nextval('public.detalle_conciliacion_id_detalle_conciliacion_seq'::regclass);


--
-- Name: disponibilidad id_disponibilidad; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.disponibilidad ALTER COLUMN id_disponibilidad SET DEFAULT nextval('public.disponibilidad_id_disponibilidad_seq'::regclass);


--
-- Name: documento_entidad id_documento_entidad; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documento_entidad ALTER COLUMN id_documento_entidad SET DEFAULT nextval('public.documento_entidad_id_documento_entidad_seq'::regclass);


--
-- Name: documento_logico id_documento_logico; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documento_logico ALTER COLUMN id_documento_logico SET DEFAULT nextval('public.documento_logico_id_documento_logico_seq'::regclass);


--
-- Name: documento_version id_documento_version; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documento_version ALTER COLUMN id_documento_version SET DEFAULT nextval('public.documento_version_id_documento_version_seq'::regclass);


--
-- Name: edificacion id_edificacion; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.edificacion ALTER COLUMN id_edificacion SET DEFAULT nextval('public.edificacion_id_edificacion_seq'::regclass);


--
-- Name: emision_numeracion id_emision_numeracion; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.emision_numeracion ALTER COLUMN id_emision_numeracion SET DEFAULT nextval('public.emision_numeracion_id_emision_numeracion_seq'::regclass);


--
-- Name: entrega_restitucion_inmueble id_entrega_restitucion; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entrega_restitucion_inmueble ALTER COLUMN id_entrega_restitucion SET DEFAULT nextval('public.entrega_restitucion_inmueble_id_entrega_restitucion_seq'::regclass);


--
-- Name: escrituracion id_escrituracion; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.escrituracion ALTER COLUMN id_escrituracion SET DEFAULT nextval('public.escrituracion_id_escrituracion_seq'::regclass);


--
-- Name: evento_auditoria id_evento_auditoria; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.evento_auditoria ALTER COLUMN id_evento_auditoria SET DEFAULT nextval('public.evento_auditoria_id_evento_auditoria_seq'::regclass);


--
-- Name: evento_numeracion id_evento_numeracion; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.evento_numeracion ALTER COLUMN id_evento_numeracion SET DEFAULT nextval('public.evento_numeracion_id_evento_numeracion_seq'::regclass);


--
-- Name: factura_servicio id_factura_servicio; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.factura_servicio ALTER COLUMN id_factura_servicio SET DEFAULT nextval('public.factura_servicio_id_factura_servicio_seq'::regclass);


--
-- Name: historial_acceso id_historial_acceso; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.historial_acceso ALTER COLUMN id_historial_acceso SET DEFAULT nextval('public.historial_acceso_id_historial_acceso_seq'::regclass);


--
-- Name: historial_catalogo id_historial_catalogo; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.historial_catalogo ALTER COLUMN id_historial_catalogo SET DEFAULT nextval('public.historial_catalogo_id_historial_catalogo_seq'::regclass);


--
-- Name: historial_parametro id_historial_parametro; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.historial_parametro ALTER COLUMN id_historial_parametro SET DEFAULT nextval('public.historial_parametro_id_historial_parametro_seq'::regclass);


--
-- Name: inmueble id_inmueble; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.inmueble ALTER COLUMN id_inmueble SET DEFAULT nextval('public.inmueble_id_inmueble_seq'::regclass);


--
-- Name: inmueble_servicio id_inmueble_servicio; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.inmueble_servicio ALTER COLUMN id_inmueble_servicio SET DEFAULT nextval('public.inmueble_servicio_id_inmueble_servicio_seq'::regclass);


--
-- Name: inmueble_sucursal id_inmueble_sucursal; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.inmueble_sucursal ALTER COLUMN id_inmueble_sucursal SET DEFAULT nextval('public.inmueble_sucursal_id_inmueble_sucursal_seq'::regclass);


--
-- Name: instalacion id_instalacion; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.instalacion ALTER COLUMN id_instalacion SET DEFAULT nextval('public.instalacion_id_instalacion_seq'::regclass);


--
-- Name: instrumento_compraventa id_instrumento_compraventa; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.instrumento_compraventa ALTER COLUMN id_instrumento_compraventa SET DEFAULT nextval('public.instrumento_compraventa_id_instrumento_compraventa_seq'::regclass);


--
-- Name: instrumento_objeto_inmobiliario id_instrumento_objeto; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.instrumento_objeto_inmobiliario ALTER COLUMN id_instrumento_objeto SET DEFAULT nextval('public.instrumento_objeto_inmobiliario_id_instrumento_objeto_seq'::regclass);


--
-- Name: item_catalogo id_item_catalogo; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.item_catalogo ALTER COLUMN id_item_catalogo SET DEFAULT nextval('public.item_catalogo_id_item_catalogo_seq'::regclass);


--
-- Name: jerarquia_item_catalogo id_jerarquia_item_catalogo; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.jerarquia_item_catalogo ALTER COLUMN id_jerarquia_item_catalogo SET DEFAULT nextval('public.jerarquia_item_catalogo_id_jerarquia_item_catalogo_seq'::regclass);


--
-- Name: lock_logico id_lock_logico; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lock_logico ALTER COLUMN id_lock_logico SET DEFAULT nextval('public.lock_logico_id_lock_logico_seq'::regclass);


--
-- Name: modificacion_locativa id_modificacion_locativa; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.modificacion_locativa ALTER COLUMN id_modificacion_locativa SET DEFAULT nextval('public.modificacion_locativa_id_modificacion_locativa_seq'::regclass);


--
-- Name: movimiento_financiero id_movimiento_financiero; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.movimiento_financiero ALTER COLUMN id_movimiento_financiero SET DEFAULT nextval('public.movimiento_financiero_id_movimiento_financiero_seq'::regclass);


--
-- Name: movimiento_tesoreria id_movimiento_tesoreria; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.movimiento_tesoreria ALTER COLUMN id_movimiento_tesoreria SET DEFAULT nextval('public.movimiento_tesoreria_id_movimiento_tesoreria_seq'::regclass);


--
-- Name: numerador_documental id_numerador_documental; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.numerador_documental ALTER COLUMN id_numerador_documental SET DEFAULT nextval('public.numerador_documental_id_numerador_documental_seq'::regclass);


--
-- Name: numerador_serie id_numerador_serie; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.numerador_serie ALTER COLUMN id_numerador_serie SET DEFAULT nextval('public.numerador_serie_id_numerador_serie_seq'::regclass);


--
-- Name: objeto_auditado id_objeto_auditado; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.objeto_auditado ALTER COLUMN id_objeto_auditado SET DEFAULT nextval('public.objeto_auditado_id_objeto_auditado_seq'::regclass);


--
-- Name: obligacion_financiera id_obligacion_financiera; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.obligacion_financiera ALTER COLUMN id_obligacion_financiera SET DEFAULT nextval('public.obligacion_financiera_id_obligacion_financiera_seq'::regclass);


--
-- Name: obligacion_obligado id_obligacion_obligado; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.obligacion_obligado ALTER COLUMN id_obligacion_obligado SET DEFAULT nextval('public.obligacion_obligado_id_obligacion_obligado_seq'::regclass);


--
-- Name: ocupacion id_ocupacion; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ocupacion ALTER COLUMN id_ocupacion SET DEFAULT nextval('public.ocupacion_id_ocupacion_seq'::regclass);


--
-- Name: operacion_auditoria id_operacion_auditoria; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.operacion_auditoria ALTER COLUMN id_operacion_auditoria SET DEFAULT nextval('public.operacion_auditoria_id_operacion_auditoria_seq'::regclass);


--
-- Name: parametro_opcion id_parametro_opcion; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.parametro_opcion ALTER COLUMN id_parametro_opcion SET DEFAULT nextval('public.parametro_opcion_id_parametro_opcion_seq'::regclass);


--
-- Name: parametro_sistema id_parametro_sistema; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.parametro_sistema ALTER COLUMN id_parametro_sistema SET DEFAULT nextval('public.parametro_sistema_id_parametro_sistema_seq'::regclass);


--
-- Name: permiso id_permiso; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.permiso ALTER COLUMN id_permiso SET DEFAULT nextval('public.permiso_id_permiso_seq'::regclass);


--
-- Name: persona id_persona; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.persona ALTER COLUMN id_persona SET DEFAULT nextval('public.persona_id_persona_seq'::regclass);


--
-- Name: persona_contacto id_persona_contacto; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.persona_contacto ALTER COLUMN id_persona_contacto SET DEFAULT nextval('public.persona_contacto_id_persona_contacto_seq'::regclass);


--
-- Name: persona_documento id_persona_documento; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.persona_documento ALTER COLUMN id_persona_documento SET DEFAULT nextval('public.persona_documento_id_persona_documento_seq'::regclass);


--
-- Name: persona_domicilio id_persona_domicilio; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.persona_domicilio ALTER COLUMN id_persona_domicilio SET DEFAULT nextval('public.persona_domicilio_id_persona_domicilio_seq'::regclass);


--
-- Name: persona_relacion id_persona_relacion; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.persona_relacion ALTER COLUMN id_persona_relacion SET DEFAULT nextval('public.persona_relacion_id_persona_relacion_seq'::regclass);


--
-- Name: relacion_generadora id_relacion_generadora; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.relacion_generadora ALTER COLUMN id_relacion_generadora SET DEFAULT nextval('public.relacion_generadora_id_relacion_generadora_seq'::regclass);


--
-- Name: relacion_persona_rol id_relacion_persona_rol; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.relacion_persona_rol ALTER COLUMN id_relacion_persona_rol SET DEFAULT nextval('public.relacion_persona_rol_id_relacion_persona_rol_seq'::regclass);


--
-- Name: representacion_poder id_representacion_poder; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.representacion_poder ALTER COLUMN id_representacion_poder SET DEFAULT nextval('public.representacion_poder_id_representacion_poder_seq'::regclass);


--
-- Name: rescision_finalizacion_alquiler id_rescision_locativa; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rescision_finalizacion_alquiler ALTER COLUMN id_rescision_locativa SET DEFAULT nextval('public.rescision_finalizacion_alquiler_id_rescision_locativa_seq'::regclass);


--
-- Name: rescision_venta id_rescision_venta; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rescision_venta ALTER COLUMN id_rescision_venta SET DEFAULT nextval('public.rescision_venta_id_rescision_venta_seq'::regclass);


--
-- Name: reserva_locativa id_reserva_locativa; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.reserva_locativa ALTER COLUMN id_reserva_locativa SET DEFAULT nextval('public.reserva_locativa_id_reserva_locativa_seq'::regclass);


--
-- Name: reserva_venta id_reserva_venta; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.reserva_venta ALTER COLUMN id_reserva_venta SET DEFAULT nextval('public.reserva_venta_id_reserva_venta_seq'::regclass);


--
-- Name: resultado_evento_auditoria id_resultado_evento_auditoria; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.resultado_evento_auditoria ALTER COLUMN id_resultado_evento_auditoria SET DEFAULT nextval('public.resultado_evento_auditoria_id_resultado_evento_auditoria_seq'::regclass);


--
-- Name: rol_participacion id_rol_participacion; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rol_participacion ALTER COLUMN id_rol_participacion SET DEFAULT nextval('public.rol_participacion_id_rol_participacion_seq'::regclass);


--
-- Name: rol_seguridad id_rol_seguridad; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rol_seguridad ALTER COLUMN id_rol_seguridad SET DEFAULT nextval('public.rol_seguridad_id_rol_seguridad_seq'::regclass);


--
-- Name: rol_seguridad_permiso id_rol_seguridad_permiso; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rol_seguridad_permiso ALTER COLUMN id_rol_seguridad_permiso SET DEFAULT nextval('public.rol_seguridad_permiso_id_rol_seguridad_permiso_seq'::regclass);


--
-- Name: seccion_configuracion id_seccion_configuracion; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.seccion_configuracion ALTER COLUMN id_seccion_configuracion SET DEFAULT nextval('public.seccion_configuracion_id_seccion_configuracion_seq'::regclass);


--
-- Name: servicio id_servicio; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.servicio ALTER COLUMN id_servicio SET DEFAULT nextval('public.servicio_id_servicio_seq'::regclass);


--
-- Name: sesion_usuario id_sesion_usuario; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sesion_usuario ALTER COLUMN id_sesion_usuario SET DEFAULT nextval('public.sesion_usuario_id_sesion_usuario_seq'::regclass);


--
-- Name: sincronizacion_operacion id_sincronizacion_operacion; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sincronizacion_operacion ALTER COLUMN id_sincronizacion_operacion SET DEFAULT nextval('public.sincronizacion_operacion_id_sincronizacion_operacion_seq'::regclass);


--
-- Name: sincronizacion_paquete id_sincronizacion_paquete; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sincronizacion_paquete ALTER COLUMN id_sincronizacion_paquete SET DEFAULT nextval('public.sincronizacion_paquete_id_sincronizacion_paquete_seq'::regclass);


--
-- Name: sincronizacion_recepcion id_sincronizacion_recepcion; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sincronizacion_recepcion ALTER COLUMN id_sincronizacion_recepcion SET DEFAULT nextval('public.sincronizacion_recepcion_id_sincronizacion_recepcion_seq'::regclass);


--
-- Name: solicitud_alquiler id_solicitud_alquiler; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.solicitud_alquiler ALTER COLUMN id_solicitud_alquiler SET DEFAULT nextval('public.solicitud_alquiler_id_solicitud_alquiler_seq'::regclass);


--
-- Name: sucursal id_sucursal; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sucursal ALTER COLUMN id_sucursal SET DEFAULT nextval('public.sucursal_id_sucursal_seq'::regclass);


--
-- Name: tipo_dato_parametro id_tipo_dato_parametro; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tipo_dato_parametro ALTER COLUMN id_tipo_dato_parametro SET DEFAULT nextval('public.tipo_dato_parametro_id_tipo_dato_parametro_seq'::regclass);


--
-- Name: tipo_documental id_tipo_documental; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tipo_documental ALTER COLUMN id_tipo_documental SET DEFAULT nextval('public.tipo_documental_id_tipo_documental_seq'::regclass);


--
-- Name: tipo_evento_auditoria id_tipo_evento_auditoria; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tipo_evento_auditoria ALTER COLUMN id_tipo_evento_auditoria SET DEFAULT nextval('public.tipo_evento_auditoria_id_tipo_evento_auditoria_seq'::regclass);


--
-- Name: unidad_funcional id_unidad_funcional; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.unidad_funcional ALTER COLUMN id_unidad_funcional SET DEFAULT nextval('public.unidad_funcional_id_unidad_funcional_seq'::regclass);


--
-- Name: unidad_funcional_servicio id_unidad_funcional_servicio; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.unidad_funcional_servicio ALTER COLUMN id_unidad_funcional_servicio SET DEFAULT nextval('public.unidad_funcional_servicio_id_unidad_funcional_servicio_seq'::regclass);


--
-- Name: usuario id_usuario; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usuario ALTER COLUMN id_usuario SET DEFAULT nextval('public.usuario_id_usuario_seq'::regclass);


--
-- Name: usuario_persona id_usuario_persona; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usuario_persona ALTER COLUMN id_usuario_persona SET DEFAULT nextval('public.usuario_persona_id_usuario_persona_seq'::regclass);


--
-- Name: usuario_rol_seguridad id_usuario_rol_seguridad; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usuario_rol_seguridad ALTER COLUMN id_usuario_rol_seguridad SET DEFAULT nextval('public.usuario_rol_seguridad_id_usuario_rol_seguridad_seq'::regclass);


--
-- Name: usuario_rol_sucursal id_usuario_rol_sucursal; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usuario_rol_sucursal ALTER COLUMN id_usuario_rol_sucursal SET DEFAULT nextval('public.usuario_rol_sucursal_id_usuario_rol_sucursal_seq'::regclass);


--
-- Name: usuario_sucursal id_usuario_sucursal; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usuario_sucursal ALTER COLUMN id_usuario_sucursal SET DEFAULT nextval('public.usuario_sucursal_id_usuario_sucursal_seq'::regclass);


--
-- Name: valor_parametro id_valor_parametro; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.valor_parametro ALTER COLUMN id_valor_parametro SET DEFAULT nextval('public.valor_parametro_id_valor_parametro_seq'::regclass);


--
-- Name: venta id_venta; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.venta ALTER COLUMN id_venta SET DEFAULT nextval('public.venta_id_venta_seq'::regclass);


--
-- Name: venta_objeto_inmobiliario id_venta_objeto; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.venta_objeto_inmobiliario ALTER COLUMN id_venta_objeto SET DEFAULT nextval('public.venta_objeto_inmobiliario_id_venta_objeto_seq'::regclass);


--
-- Name: ajuste_alquiler ajuste_alquiler_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ajuste_alquiler
    ADD CONSTRAINT ajuste_alquiler_pkey PRIMARY KEY (id_ajuste_alquiler);


--
-- Name: alcance_autorizacion alcance_autorizacion_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alcance_autorizacion
    ADD CONSTRAINT alcance_autorizacion_pkey PRIMARY KEY (id_alcance_autorizacion);


--
-- Name: alcance_parametro alcance_parametro_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alcance_parametro
    ADD CONSTRAINT alcance_parametro_pkey PRIMARY KEY (id_alcance_parametro);


--
-- Name: aplicacion_financiera aplicacion_financiera_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.aplicacion_financiera
    ADD CONSTRAINT aplicacion_financiera_pkey PRIMARY KEY (id_aplicacion_financiera);


--
-- Name: archivo_digital archivo_digital_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.archivo_digital
    ADD CONSTRAINT archivo_digital_pkey PRIMARY KEY (id_archivo_digital);


--
-- Name: cartera_locativa cartera_locativa_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.cartera_locativa
    ADD CONSTRAINT cartera_locativa_pkey PRIMARY KEY (id_cartera_locativa);


--
-- Name: catalogo_maestro catalogo_maestro_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.catalogo_maestro
    ADD CONSTRAINT catalogo_maestro_pkey PRIMARY KEY (id_catalogo_maestro);


--
-- Name: cesion cesion_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.cesion
    ADD CONSTRAINT cesion_pkey PRIMARY KEY (id_cesion);


--
-- Name: cliente_comprador cliente_comprador_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.cliente_comprador
    ADD CONSTRAINT cliente_comprador_pkey PRIMARY KEY (id_cliente_comprador);


--
-- Name: composicion_obligacion composicion_obligacion_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.composicion_obligacion
    ADD CONSTRAINT composicion_obligacion_pkey PRIMARY KEY (id_composicion_obligacion);


--
-- Name: concepto_financiero concepto_financiero_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.concepto_financiero
    ADD CONSTRAINT concepto_financiero_pkey PRIMARY KEY (id_concepto_financiero);


--
-- Name: conciliacion_bancaria conciliacion_bancaria_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.conciliacion_bancaria
    ADD CONSTRAINT conciliacion_bancaria_pkey PRIMARY KEY (id_conciliacion_bancaria);


--
-- Name: condicion_economica_alquiler condicion_economica_alquiler_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.condicion_economica_alquiler
    ADD CONSTRAINT condicion_economica_alquiler_pkey PRIMARY KEY (id_condicion_economica);


--
-- Name: configuracion_general configuracion_general_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.configuracion_general
    ADD CONSTRAINT configuracion_general_pkey PRIMARY KEY (id_configuracion_general);


--
-- Name: conflicto_sincronizacion conflicto_sincronizacion_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.conflicto_sincronizacion
    ADD CONSTRAINT conflicto_sincronizacion_pkey PRIMARY KEY (id_conflicto_sincronizacion);


--
-- Name: contrato_alquiler contrato_alquiler_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contrato_alquiler
    ADD CONSTRAINT contrato_alquiler_pkey PRIMARY KEY (id_contrato_alquiler);


--
-- Name: contrato_objeto_locativo contrato_objeto_locativo_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contrato_objeto_locativo
    ADD CONSTRAINT contrato_objeto_locativo_pkey PRIMARY KEY (id_contrato_objeto);


--
-- Name: credencial_usuario credencial_usuario_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.credencial_usuario
    ADD CONSTRAINT credencial_usuario_pkey PRIMARY KEY (id_credencial_usuario);


--
-- Name: cuenta_financiera cuenta_financiera_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.cuenta_financiera
    ADD CONSTRAINT cuenta_financiera_pkey PRIMARY KEY (id_cuenta_financiera);


--
-- Name: denegacion_explicita denegacion_explicita_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.denegacion_explicita
    ADD CONSTRAINT denegacion_explicita_pkey PRIMARY KEY (id_denegacion_explicita);


--
-- Name: desarrollo desarrollo_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.desarrollo
    ADD CONSTRAINT desarrollo_pkey PRIMARY KEY (id_desarrollo);


--
-- Name: desarrollo_sucursal desarrollo_sucursal_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.desarrollo_sucursal
    ADD CONSTRAINT desarrollo_sucursal_pkey PRIMARY KEY (id_desarrollo_sucursal);


--
-- Name: detalle_cambio_auditoria detalle_cambio_auditoria_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.detalle_cambio_auditoria
    ADD CONSTRAINT detalle_cambio_auditoria_pkey PRIMARY KEY (id_detalle_cambio_auditoria);


--
-- Name: detalle_conciliacion detalle_conciliacion_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.detalle_conciliacion
    ADD CONSTRAINT detalle_conciliacion_pkey PRIMARY KEY (id_detalle_conciliacion);


--
-- Name: disponibilidad disponibilidad_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.disponibilidad
    ADD CONSTRAINT disponibilidad_pkey PRIMARY KEY (id_disponibilidad);


--
-- Name: documento_entidad documento_entidad_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documento_entidad
    ADD CONSTRAINT documento_entidad_pkey PRIMARY KEY (id_documento_entidad);


--
-- Name: documento_logico documento_logico_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documento_logico
    ADD CONSTRAINT documento_logico_pkey PRIMARY KEY (id_documento_logico);


--
-- Name: documento_version documento_version_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documento_version
    ADD CONSTRAINT documento_version_pkey PRIMARY KEY (id_documento_version);


--
-- Name: edificacion edificacion_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.edificacion
    ADD CONSTRAINT edificacion_pkey PRIMARY KEY (id_edificacion);


--
-- Name: emision_numeracion emision_numeracion_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.emision_numeracion
    ADD CONSTRAINT emision_numeracion_pkey PRIMARY KEY (id_emision_numeracion);


--
-- Name: entrega_restitucion_inmueble entrega_restitucion_inmueble_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entrega_restitucion_inmueble
    ADD CONSTRAINT entrega_restitucion_inmueble_pkey PRIMARY KEY (id_entrega_restitucion);


--
-- Name: escrituracion escrituracion_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.escrituracion
    ADD CONSTRAINT escrituracion_pkey PRIMARY KEY (id_escrituracion);


--
-- Name: outbox_event outbox_event_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.outbox_event
    ADD CONSTRAINT outbox_event_pkey PRIMARY KEY (id);


--
-- Name: evento_auditoria evento_auditoria_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.evento_auditoria
    ADD CONSTRAINT evento_auditoria_pkey PRIMARY KEY (id_evento_auditoria);


--
-- Name: evento_numeracion evento_numeracion_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.evento_numeracion
    ADD CONSTRAINT evento_numeracion_pkey PRIMARY KEY (id_evento_numeracion);


--
-- Name: factura_servicio factura_servicio_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.factura_servicio
    ADD CONSTRAINT factura_servicio_pkey PRIMARY KEY (id_factura_servicio);


--
-- Name: historial_acceso historial_acceso_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.historial_acceso
    ADD CONSTRAINT historial_acceso_pkey PRIMARY KEY (id_historial_acceso);


--
-- Name: historial_catalogo historial_catalogo_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.historial_catalogo
    ADD CONSTRAINT historial_catalogo_pkey PRIMARY KEY (id_historial_catalogo);


--
-- Name: historial_parametro historial_parametro_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.historial_parametro
    ADD CONSTRAINT historial_parametro_pkey PRIMARY KEY (id_historial_parametro);


--
-- Name: inmueble inmueble_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.inmueble
    ADD CONSTRAINT inmueble_pkey PRIMARY KEY (id_inmueble);


--
-- Name: inmueble_servicio inmueble_servicio_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.inmueble_servicio
    ADD CONSTRAINT inmueble_servicio_pkey PRIMARY KEY (id_inmueble_servicio);


--
-- Name: inmueble_sucursal inmueble_sucursal_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.inmueble_sucursal
    ADD CONSTRAINT inmueble_sucursal_pkey PRIMARY KEY (id_inmueble_sucursal);


--
-- Name: instalacion instalacion_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.instalacion
    ADD CONSTRAINT instalacion_pkey PRIMARY KEY (id_instalacion);


--
-- Name: instrumento_compraventa instrumento_compraventa_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.instrumento_compraventa
    ADD CONSTRAINT instrumento_compraventa_pkey PRIMARY KEY (id_instrumento_compraventa);


--
-- Name: instrumento_objeto_inmobiliario instrumento_objeto_inmobiliario_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.instrumento_objeto_inmobiliario
    ADD CONSTRAINT instrumento_objeto_inmobiliario_pkey PRIMARY KEY (id_instrumento_objeto);


--
-- Name: item_catalogo item_catalogo_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.item_catalogo
    ADD CONSTRAINT item_catalogo_pkey PRIMARY KEY (id_item_catalogo);


--
-- Name: jerarquia_item_catalogo jerarquia_item_catalogo_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.jerarquia_item_catalogo
    ADD CONSTRAINT jerarquia_item_catalogo_pkey PRIMARY KEY (id_jerarquia_item_catalogo);


--
-- Name: lock_logico lock_logico_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lock_logico
    ADD CONSTRAINT lock_logico_pkey PRIMARY KEY (id_lock_logico);


--
-- Name: modificacion_locativa modificacion_locativa_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.modificacion_locativa
    ADD CONSTRAINT modificacion_locativa_pkey PRIMARY KEY (id_modificacion_locativa);


--
-- Name: movimiento_financiero movimiento_financiero_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.movimiento_financiero
    ADD CONSTRAINT movimiento_financiero_pkey PRIMARY KEY (id_movimiento_financiero);


--
-- Name: movimiento_tesoreria movimiento_tesoreria_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.movimiento_tesoreria
    ADD CONSTRAINT movimiento_tesoreria_pkey PRIMARY KEY (id_movimiento_tesoreria);


--
-- Name: numerador_documental numerador_documental_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.numerador_documental
    ADD CONSTRAINT numerador_documental_pkey PRIMARY KEY (id_numerador_documental);


--
-- Name: numerador_serie numerador_serie_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.numerador_serie
    ADD CONSTRAINT numerador_serie_pkey PRIMARY KEY (id_numerador_serie);


--
-- Name: objeto_auditado objeto_auditado_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.objeto_auditado
    ADD CONSTRAINT objeto_auditado_pkey PRIMARY KEY (id_objeto_auditado);


--
-- Name: obligacion_financiera obligacion_financiera_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.obligacion_financiera
    ADD CONSTRAINT obligacion_financiera_pkey PRIMARY KEY (id_obligacion_financiera);


--
-- Name: obligacion_obligado obligacion_obligado_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.obligacion_obligado
    ADD CONSTRAINT obligacion_obligado_pkey PRIMARY KEY (id_obligacion_obligado);


--
-- Name: ocupacion ocupacion_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ocupacion
    ADD CONSTRAINT ocupacion_pkey PRIMARY KEY (id_ocupacion);


--
-- Name: operacion_auditoria operacion_auditoria_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.operacion_auditoria
    ADD CONSTRAINT operacion_auditoria_pkey PRIMARY KEY (id_operacion_auditoria);


--
-- Name: parametro_opcion parametro_opcion_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.parametro_opcion
    ADD CONSTRAINT parametro_opcion_pkey PRIMARY KEY (id_parametro_opcion);


--
-- Name: parametro_sistema parametro_sistema_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.parametro_sistema
    ADD CONSTRAINT parametro_sistema_pkey PRIMARY KEY (id_parametro_sistema);


--
-- Name: permiso permiso_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.permiso
    ADD CONSTRAINT permiso_pkey PRIMARY KEY (id_permiso);


--
-- Name: persona_contacto persona_contacto_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.persona_contacto
    ADD CONSTRAINT persona_contacto_pkey PRIMARY KEY (id_persona_contacto);


--
-- Name: persona_documento persona_documento_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.persona_documento
    ADD CONSTRAINT persona_documento_pkey PRIMARY KEY (id_persona_documento);


--
-- Name: persona_domicilio persona_domicilio_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.persona_domicilio
    ADD CONSTRAINT persona_domicilio_pkey PRIMARY KEY (id_persona_domicilio);


--
-- Name: persona persona_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.persona
    ADD CONSTRAINT persona_pkey PRIMARY KEY (id_persona);


--
-- Name: persona_relacion persona_relacion_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.persona_relacion
    ADD CONSTRAINT persona_relacion_pkey PRIMARY KEY (id_persona_relacion);


--
-- Name: relacion_generadora relacion_generadora_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.relacion_generadora
    ADD CONSTRAINT relacion_generadora_pkey PRIMARY KEY (id_relacion_generadora);


--
-- Name: relacion_persona_rol relacion_persona_rol_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.relacion_persona_rol
    ADD CONSTRAINT relacion_persona_rol_pkey PRIMARY KEY (id_relacion_persona_rol);


--
-- Name: representacion_poder representacion_poder_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.representacion_poder
    ADD CONSTRAINT representacion_poder_pkey PRIMARY KEY (id_representacion_poder);


--
-- Name: rescision_finalizacion_alquiler rescision_finalizacion_alquiler_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rescision_finalizacion_alquiler
    ADD CONSTRAINT rescision_finalizacion_alquiler_pkey PRIMARY KEY (id_rescision_locativa);


--
-- Name: rescision_venta rescision_venta_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rescision_venta
    ADD CONSTRAINT rescision_venta_pkey PRIMARY KEY (id_rescision_venta);


--
-- Name: reserva_locativa reserva_locativa_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.reserva_locativa
    ADD CONSTRAINT reserva_locativa_pkey PRIMARY KEY (id_reserva_locativa);


--
-- Name: reserva_venta reserva_venta_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.reserva_venta
    ADD CONSTRAINT reserva_venta_pkey PRIMARY KEY (id_reserva_venta);


--
-- Name: resultado_evento_auditoria resultado_evento_auditoria_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.resultado_evento_auditoria
    ADD CONSTRAINT resultado_evento_auditoria_pkey PRIMARY KEY (id_resultado_evento_auditoria);


--
-- Name: rol_participacion rol_participacion_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rol_participacion
    ADD CONSTRAINT rol_participacion_pkey PRIMARY KEY (id_rol_participacion);


--
-- Name: rol_seguridad_permiso rol_seguridad_permiso_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rol_seguridad_permiso
    ADD CONSTRAINT rol_seguridad_permiso_pkey PRIMARY KEY (id_rol_seguridad_permiso);


--
-- Name: rol_seguridad rol_seguridad_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rol_seguridad
    ADD CONSTRAINT rol_seguridad_pkey PRIMARY KEY (id_rol_seguridad);


--
-- Name: seccion_configuracion seccion_configuracion_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.seccion_configuracion
    ADD CONSTRAINT seccion_configuracion_pkey PRIMARY KEY (id_seccion_configuracion);


--
-- Name: servicio servicio_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.servicio
    ADD CONSTRAINT servicio_pkey PRIMARY KEY (id_servicio);


--
-- Name: sesion_usuario sesion_usuario_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sesion_usuario
    ADD CONSTRAINT sesion_usuario_pkey PRIMARY KEY (id_sesion_usuario);


--
-- Name: sincronizacion_operacion sincronizacion_operacion_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sincronizacion_operacion
    ADD CONSTRAINT sincronizacion_operacion_pkey PRIMARY KEY (id_sincronizacion_operacion);


--
-- Name: sincronizacion_paquete sincronizacion_paquete_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sincronizacion_paquete
    ADD CONSTRAINT sincronizacion_paquete_pkey PRIMARY KEY (id_sincronizacion_paquete);


--
-- Name: sincronizacion_recepcion sincronizacion_recepcion_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sincronizacion_recepcion
    ADD CONSTRAINT sincronizacion_recepcion_pkey PRIMARY KEY (id_sincronizacion_recepcion);


--
-- Name: solicitud_alquiler solicitud_alquiler_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.solicitud_alquiler
    ADD CONSTRAINT solicitud_alquiler_pkey PRIMARY KEY (id_solicitud_alquiler);


--
-- Name: sucursal sucursal_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sucursal
    ADD CONSTRAINT sucursal_pkey PRIMARY KEY (id_sucursal);


--
-- Name: tipo_dato_parametro tipo_dato_parametro_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tipo_dato_parametro
    ADD CONSTRAINT tipo_dato_parametro_pkey PRIMARY KEY (id_tipo_dato_parametro);


--
-- Name: tipo_documental tipo_documental_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tipo_documental
    ADD CONSTRAINT tipo_documental_pkey PRIMARY KEY (id_tipo_documental);


--
-- Name: tipo_evento_auditoria tipo_evento_auditoria_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tipo_evento_auditoria
    ADD CONSTRAINT tipo_evento_auditoria_pkey PRIMARY KEY (id_tipo_evento_auditoria);


--
-- Name: unidad_funcional unidad_funcional_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.unidad_funcional
    ADD CONSTRAINT unidad_funcional_pkey PRIMARY KEY (id_unidad_funcional);


--
-- Name: unidad_funcional_servicio unidad_funcional_servicio_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.unidad_funcional_servicio
    ADD CONSTRAINT unidad_funcional_servicio_pkey PRIMARY KEY (id_unidad_funcional_servicio);


--
-- Name: ajuste_alquiler uq_ajuste_alquiler_uid_global; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ajuste_alquiler
    ADD CONSTRAINT uq_ajuste_alquiler_uid_global UNIQUE (uid_global);


--
-- Name: alcance_parametro uq_alcance_parametro; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alcance_parametro
    ADD CONSTRAINT uq_alcance_parametro UNIQUE (codigo_alcance);


--
-- Name: aplicacion_financiera uq_aplicacion_financiera_uid_global; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.aplicacion_financiera
    ADD CONSTRAINT uq_aplicacion_financiera_uid_global UNIQUE (uid_global);


--
-- Name: archivo_digital uq_archivo_digital_uid_global; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.archivo_digital
    ADD CONSTRAINT uq_archivo_digital_uid_global UNIQUE (uid_global);


--
-- Name: cartera_locativa uq_cartera_codigo; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.cartera_locativa
    ADD CONSTRAINT uq_cartera_codigo UNIQUE (codigo_cartera);


--
-- Name: cartera_locativa uq_cartera_locativa_uid_global; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.cartera_locativa
    ADD CONSTRAINT uq_cartera_locativa_uid_global UNIQUE (uid_global);


--
-- Name: catalogo_maestro uq_catalogo_maestro; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.catalogo_maestro
    ADD CONSTRAINT uq_catalogo_maestro UNIQUE (codigo_catalogo_maestro);


--
-- Name: cesion uq_cesion_uid_global; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.cesion
    ADD CONSTRAINT uq_cesion_uid_global UNIQUE (uid_global);


--
-- Name: cliente_comprador uq_cliente_comprador_codigo; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.cliente_comprador
    ADD CONSTRAINT uq_cliente_comprador_codigo UNIQUE (codigo_cliente_comprador);


--
-- Name: cliente_comprador uq_cliente_comprador_uid_global; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.cliente_comprador
    ADD CONSTRAINT uq_cliente_comprador_uid_global UNIQUE (uid_global);


--
-- Name: cliente_comprador uq_cliente_persona; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.cliente_comprador
    ADD CONSTRAINT uq_cliente_persona UNIQUE (id_persona);


--
-- Name: composicion_obligacion uq_composicion_obligacion_uid_global; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.composicion_obligacion
    ADD CONSTRAINT uq_composicion_obligacion_uid_global UNIQUE (uid_global);


--
-- Name: concepto_financiero uq_concepto_codigo; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.concepto_financiero
    ADD CONSTRAINT uq_concepto_codigo UNIQUE (codigo_concepto_financiero);


--
-- Name: concepto_financiero uq_concepto_financiero_uid_global; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.concepto_financiero
    ADD CONSTRAINT uq_concepto_financiero_uid_global UNIQUE (uid_global);


--
-- Name: conciliacion_bancaria uq_conciliacion_bancaria_uid_global; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.conciliacion_bancaria
    ADD CONSTRAINT uq_conciliacion_bancaria_uid_global UNIQUE (uid_global);


--
-- Name: condicion_economica_alquiler uq_condicion_economica_alquiler_uid_global; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.condicion_economica_alquiler
    ADD CONSTRAINT uq_condicion_economica_alquiler_uid_global UNIQUE (uid_global);


--
-- Name: configuracion_general uq_configuracion_general; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.configuracion_general
    ADD CONSTRAINT uq_configuracion_general UNIQUE (codigo_configuracion);


--
-- Name: conflicto_sincronizacion uq_conflicto_op_id; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.conflicto_sincronizacion
    ADD CONSTRAINT uq_conflicto_op_id UNIQUE (op_id);


--
-- Name: contrato_alquiler uq_contrato_alquiler_uid_global; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contrato_alquiler
    ADD CONSTRAINT uq_contrato_alquiler_uid_global UNIQUE (uid_global);


--
-- Name: contrato_alquiler uq_contrato_codigo; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contrato_alquiler
    ADD CONSTRAINT uq_contrato_codigo UNIQUE (codigo_contrato);


--
-- Name: contrato_objeto_locativo uq_contrato_objeto_locativo_uid_global; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contrato_objeto_locativo
    ADD CONSTRAINT uq_contrato_objeto_locativo_uid_global UNIQUE (uid_global);


--
-- Name: cuenta_financiera uq_cuenta_financiera_uid_global; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.cuenta_financiera
    ADD CONSTRAINT uq_cuenta_financiera_uid_global UNIQUE (uid_global);


--
-- Name: desarrollo uq_desarrollo_codigo; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.desarrollo
    ADD CONSTRAINT uq_desarrollo_codigo UNIQUE (codigo_desarrollo);


--
-- Name: desarrollo_sucursal uq_desarrollo_sucursal_uid_global; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.desarrollo_sucursal
    ADD CONSTRAINT uq_desarrollo_sucursal_uid_global UNIQUE (uid_global);


--
-- Name: desarrollo uq_desarrollo_uid_global; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.desarrollo
    ADD CONSTRAINT uq_desarrollo_uid_global UNIQUE (uid_global);


--
-- Name: detalle_conciliacion uq_detalle_conciliacion_uid_global; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.detalle_conciliacion
    ADD CONSTRAINT uq_detalle_conciliacion_uid_global UNIQUE (uid_global);


--
-- Name: disponibilidad uq_disponibilidad_uid_global; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.disponibilidad
    ADD CONSTRAINT uq_disponibilidad_uid_global UNIQUE (uid_global);


--
-- Name: documento_version uq_doc_version; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documento_version
    ADD CONSTRAINT uq_doc_version UNIQUE (id_documento_logico, numero_version);


--
-- Name: documento_entidad uq_documento_entidad_uid_global; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documento_entidad
    ADD CONSTRAINT uq_documento_entidad_uid_global UNIQUE (uid_global);


--
-- Name: documento_logico uq_documento_logico_uid_global; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documento_logico
    ADD CONSTRAINT uq_documento_logico_uid_global UNIQUE (uid_global);


--
-- Name: documento_version uq_documento_version_uid_global; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documento_version
    ADD CONSTRAINT uq_documento_version_uid_global UNIQUE (uid_global);


--
-- Name: edificacion uq_edificacion_uid_global; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.edificacion
    ADD CONSTRAINT uq_edificacion_uid_global UNIQUE (uid_global);


--
-- Name: emision_numeracion uq_emision_numeracion_uid_global; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.emision_numeracion
    ADD CONSTRAINT uq_emision_numeracion_uid_global UNIQUE (uid_global);


--
-- Name: entrega_restitucion_inmueble uq_entrega_restitucion_inmueble_uid_global; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entrega_restitucion_inmueble
    ADD CONSTRAINT uq_entrega_restitucion_inmueble_uid_global UNIQUE (uid_global);


--
-- Name: escrituracion uq_escrituracion_uid_global; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.escrituracion
    ADD CONSTRAINT uq_escrituracion_uid_global UNIQUE (uid_global);


--
-- Name: evento_numeracion uq_evento_numeracion_uid_global; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.evento_numeracion
    ADD CONSTRAINT uq_evento_numeracion_uid_global UNIQUE (uid_global);


--
-- Name: factura_servicio uq_factura_servicio_uid_global; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.factura_servicio
    ADD CONSTRAINT uq_factura_servicio_uid_global UNIQUE (uid_global);


--
-- Name: inmueble uq_inmueble_codigo; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.inmueble
    ADD CONSTRAINT uq_inmueble_codigo UNIQUE (codigo_inmueble);


--
-- Name: inmueble_servicio uq_inmueble_servicio_uid_global; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.inmueble_servicio
    ADD CONSTRAINT uq_inmueble_servicio_uid_global UNIQUE (uid_global);


--
-- Name: inmueble_sucursal uq_inmueble_sucursal_uid_global; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.inmueble_sucursal
    ADD CONSTRAINT uq_inmueble_sucursal_uid_global UNIQUE (uid_global);


--
-- Name: inmueble uq_inmueble_uid_global; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.inmueble
    ADD CONSTRAINT uq_inmueble_uid_global UNIQUE (uid_global);


--
-- Name: instalacion uq_instalacion_codigo; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.instalacion
    ADD CONSTRAINT uq_instalacion_codigo UNIQUE (codigo_instalacion);


--
-- Name: instalacion uq_instalacion_uid_global; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.instalacion
    ADD CONSTRAINT uq_instalacion_uid_global UNIQUE (uid_global);


--
-- Name: instrumento_compraventa uq_instrumento_compraventa_uid_global; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.instrumento_compraventa
    ADD CONSTRAINT uq_instrumento_compraventa_uid_global UNIQUE (uid_global);


--
-- Name: instrumento_objeto_inmobiliario uq_instrumento_objeto_uid_global; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.instrumento_objeto_inmobiliario
    ADD CONSTRAINT uq_instrumento_objeto_uid_global UNIQUE (uid_global);


--
-- Name: item_catalogo uq_item_catalogo; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.item_catalogo
    ADD CONSTRAINT uq_item_catalogo UNIQUE (id_catalogo_maestro, codigo_item_catalogo);


--
-- Name: modificacion_locativa uq_modificacion_locativa_uid_global; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.modificacion_locativa
    ADD CONSTRAINT uq_modificacion_locativa_uid_global UNIQUE (uid_global);


--
-- Name: movimiento_financiero uq_movimiento_financiero_uid_global; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.movimiento_financiero
    ADD CONSTRAINT uq_movimiento_financiero_uid_global UNIQUE (uid_global);


--
-- Name: movimiento_tesoreria uq_movimiento_tesoreria_uid_global; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.movimiento_tesoreria
    ADD CONSTRAINT uq_movimiento_tesoreria_uid_global UNIQUE (uid_global);


--
-- Name: numerador_documental uq_numerador_codigo; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.numerador_documental
    ADD CONSTRAINT uq_numerador_codigo UNIQUE (codigo_numerador);


--
-- Name: numerador_documental uq_numerador_documental_uid_global; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.numerador_documental
    ADD CONSTRAINT uq_numerador_documental_uid_global UNIQUE (uid_global);


--
-- Name: numerador_serie uq_numerador_serie_uid_global; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.numerador_serie
    ADD CONSTRAINT uq_numerador_serie_uid_global UNIQUE (uid_global);


--
-- Name: obligacion_financiera uq_obligacion_financiera_uid_global; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.obligacion_financiera
    ADD CONSTRAINT uq_obligacion_financiera_uid_global UNIQUE (uid_global);


--
-- Name: obligacion_obligado uq_obligacion_obligado_uid_global; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.obligacion_obligado
    ADD CONSTRAINT uq_obligacion_obligado_uid_global UNIQUE (uid_global);


--
-- Name: ocupacion uq_ocupacion_uid_global; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ocupacion
    ADD CONSTRAINT uq_ocupacion_uid_global UNIQUE (uid_global);


--
-- Name: parametro_sistema uq_parametro_sistema; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.parametro_sistema
    ADD CONSTRAINT uq_parametro_sistema UNIQUE (codigo_parametro);


--
-- Name: permiso uq_permiso_codigo; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.permiso
    ADD CONSTRAINT uq_permiso_codigo UNIQUE (codigo_permiso);


--
-- Name: persona uq_persona_codigo; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.persona
    ADD CONSTRAINT uq_persona_codigo UNIQUE (codigo_persona);


--
-- Name: persona_contacto uq_persona_contacto_uid_global; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.persona_contacto
    ADD CONSTRAINT uq_persona_contacto_uid_global UNIQUE (uid_global);


--
-- Name: persona uq_persona_cuit_cuil; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.persona
    ADD CONSTRAINT uq_persona_cuit_cuil UNIQUE (cuit_cuil);


--
-- Name: persona_documento uq_persona_documento_uid_global; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.persona_documento
    ADD CONSTRAINT uq_persona_documento_uid_global UNIQUE (uid_global);


--
-- Name: persona_domicilio uq_persona_domicilio_uid_global; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.persona_domicilio
    ADD CONSTRAINT uq_persona_domicilio_uid_global UNIQUE (uid_global);


--
-- Name: persona_relacion uq_persona_relacion_uid_global; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.persona_relacion
    ADD CONSTRAINT uq_persona_relacion_uid_global UNIQUE (uid_global);


--
-- Name: persona uq_persona_uid_global; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.persona
    ADD CONSTRAINT uq_persona_uid_global UNIQUE (uid_global);


--
-- Name: relacion_generadora uq_relacion_generadora_uid_global; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.relacion_generadora
    ADD CONSTRAINT uq_relacion_generadora_uid_global UNIQUE (uid_global);


--
-- Name: relacion_persona_rol uq_relacion_persona_rol_uid_global; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.relacion_persona_rol
    ADD CONSTRAINT uq_relacion_persona_rol_uid_global UNIQUE (uid_global);


--
-- Name: representacion_poder uq_representacion_poder_uid_global; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.representacion_poder
    ADD CONSTRAINT uq_representacion_poder_uid_global UNIQUE (uid_global);


--
-- Name: rescision_finalizacion_alquiler uq_rescision_finalizacion_alquiler_uid_global; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rescision_finalizacion_alquiler
    ADD CONSTRAINT uq_rescision_finalizacion_alquiler_uid_global UNIQUE (uid_global);


--
-- Name: rescision_venta uq_rescision_venta_uid_global; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rescision_venta
    ADD CONSTRAINT uq_rescision_venta_uid_global UNIQUE (uid_global);


--
-- Name: reserva_venta uq_reserva_codigo; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.reserva_venta
    ADD CONSTRAINT uq_reserva_codigo UNIQUE (codigo_reserva);


--
-- Name: reserva_locativa uq_reserva_loc_codigo; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.reserva_locativa
    ADD CONSTRAINT uq_reserva_loc_codigo UNIQUE (codigo_reserva);


--
-- Name: reserva_locativa uq_reserva_locativa_uid_global; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.reserva_locativa
    ADD CONSTRAINT uq_reserva_locativa_uid_global UNIQUE (uid_global);


--
-- Name: reserva_venta uq_reserva_venta_uid_global; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.reserva_venta
    ADD CONSTRAINT uq_reserva_venta_uid_global UNIQUE (uid_global);


--
-- Name: resultado_evento_auditoria uq_resultado_evento_auditoria; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.resultado_evento_auditoria
    ADD CONSTRAINT uq_resultado_evento_auditoria UNIQUE (codigo_resultado);


--
-- Name: rol_participacion uq_rol_codigo; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rol_participacion
    ADD CONSTRAINT uq_rol_codigo UNIQUE (codigo_rol);


--
-- Name: rol_participacion uq_rol_participacion_uid_global; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rol_participacion
    ADD CONSTRAINT uq_rol_participacion_uid_global UNIQUE (uid_global);


--
-- Name: rol_seguridad uq_rol_seguridad; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rol_seguridad
    ADD CONSTRAINT uq_rol_seguridad UNIQUE (codigo_rol);


--
-- Name: seccion_configuracion uq_seccion_configuracion; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.seccion_configuracion
    ADD CONSTRAINT uq_seccion_configuracion UNIQUE (codigo_seccion);


--
-- Name: numerador_serie uq_serie; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.numerador_serie
    ADD CONSTRAINT uq_serie UNIQUE (id_numerador_documental, codigo_serie, id_sucursal);


--
-- Name: servicio uq_servicio_codigo; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.servicio
    ADD CONSTRAINT uq_servicio_codigo UNIQUE (codigo_servicio);


--
-- Name: servicio uq_servicio_uid_global; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.servicio
    ADD CONSTRAINT uq_servicio_uid_global UNIQUE (uid_global);


--
-- Name: sesion_usuario uq_sesion_token; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sesion_usuario
    ADD CONSTRAINT uq_sesion_token UNIQUE (token_sesion);


--
-- Name: sincronizacion_operacion uq_sinc_operacion_op_id; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sincronizacion_operacion
    ADD CONSTRAINT uq_sinc_operacion_op_id UNIQUE (op_id);


--
-- Name: sincronizacion_operacion uq_sinc_operacion_paquete_orden; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sincronizacion_operacion
    ADD CONSTRAINT uq_sinc_operacion_paquete_orden UNIQUE (id_sincronizacion_paquete, orden_en_paquete);


--
-- Name: sincronizacion_paquete uq_sinc_paquete_codigo; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sincronizacion_paquete
    ADD CONSTRAINT uq_sinc_paquete_codigo UNIQUE (codigo_paquete);


--
-- Name: sincronizacion_recepcion uq_sinc_recepcion_op_inst; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sincronizacion_recepcion
    ADD CONSTRAINT uq_sinc_recepcion_op_inst UNIQUE (op_id, id_instalacion_receptora);


--
-- Name: solicitud_alquiler uq_solicitud_alquiler_uid_global; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.solicitud_alquiler
    ADD CONSTRAINT uq_solicitud_alquiler_uid_global UNIQUE (uid_global);


--
-- Name: solicitud_alquiler uq_solicitud_codigo; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.solicitud_alquiler
    ADD CONSTRAINT uq_solicitud_codigo UNIQUE (codigo_solicitud);


--
-- Name: sucursal uq_sucursal_codigo; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sucursal
    ADD CONSTRAINT uq_sucursal_codigo UNIQUE (codigo_sucursal);


--
-- Name: sucursal uq_sucursal_uid_global; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sucursal
    ADD CONSTRAINT uq_sucursal_uid_global UNIQUE (uid_global);


--
-- Name: tipo_dato_parametro uq_tipo_dato_parametro; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tipo_dato_parametro
    ADD CONSTRAINT uq_tipo_dato_parametro UNIQUE (codigo_tipo_dato);


--
-- Name: tipo_documental uq_tipo_doc_codigo; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tipo_documental
    ADD CONSTRAINT uq_tipo_doc_codigo UNIQUE (codigo_tipo_documental);


--
-- Name: tipo_documental uq_tipo_documental_uid_global; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tipo_documental
    ADD CONSTRAINT uq_tipo_documental_uid_global UNIQUE (uid_global);


--
-- Name: tipo_evento_auditoria uq_tipo_evento_auditoria; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tipo_evento_auditoria
    ADD CONSTRAINT uq_tipo_evento_auditoria UNIQUE (codigo_tipo_evento);


--
-- Name: unidad_funcional uq_unidad_codigo; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.unidad_funcional
    ADD CONSTRAINT uq_unidad_codigo UNIQUE (codigo_unidad);


--
-- Name: unidad_funcional_servicio uq_unidad_funcional_servicio_uid_global; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.unidad_funcional_servicio
    ADD CONSTRAINT uq_unidad_funcional_servicio_uid_global UNIQUE (uid_global);


--
-- Name: unidad_funcional uq_unidad_funcional_uid_global; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.unidad_funcional
    ADD CONSTRAINT uq_unidad_funcional_uid_global UNIQUE (uid_global);


--
-- Name: usuario uq_usuario_codigo; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usuario
    ADD CONSTRAINT uq_usuario_codigo UNIQUE (codigo_usuario);


--
-- Name: usuario uq_usuario_login; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usuario
    ADD CONSTRAINT uq_usuario_login UNIQUE (login);


--
-- Name: venta uq_venta_codigo; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.venta
    ADD CONSTRAINT uq_venta_codigo UNIQUE (codigo_venta);


--
-- Name: venta_objeto_inmobiliario uq_venta_objeto_uid_global; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.venta_objeto_inmobiliario
    ADD CONSTRAINT uq_venta_objeto_uid_global UNIQUE (uid_global);


--
-- Name: venta uq_venta_uid_global; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.venta
    ADD CONSTRAINT uq_venta_uid_global UNIQUE (uid_global);


--
-- Name: usuario_persona usuario_persona_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usuario_persona
    ADD CONSTRAINT usuario_persona_pkey PRIMARY KEY (id_usuario_persona);


--
-- Name: usuario usuario_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usuario
    ADD CONSTRAINT usuario_pkey PRIMARY KEY (id_usuario);


--
-- Name: usuario_rol_seguridad usuario_rol_seguridad_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usuario_rol_seguridad
    ADD CONSTRAINT usuario_rol_seguridad_pkey PRIMARY KEY (id_usuario_rol_seguridad);


--
-- Name: usuario_rol_sucursal usuario_rol_sucursal_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usuario_rol_sucursal
    ADD CONSTRAINT usuario_rol_sucursal_pkey PRIMARY KEY (id_usuario_rol_sucursal);


--
-- Name: usuario_sucursal usuario_sucursal_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usuario_sucursal
    ADD CONSTRAINT usuario_sucursal_pkey PRIMARY KEY (id_usuario_sucursal);


--
-- Name: valor_parametro valor_parametro_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.valor_parametro
    ADD CONSTRAINT valor_parametro_pkey PRIMARY KEY (id_valor_parametro);


--
-- Name: venta_objeto_inmobiliario venta_objeto_inmobiliario_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.venta_objeto_inmobiliario
    ADD CONSTRAINT venta_objeto_inmobiliario_pkey PRIMARY KEY (id_venta_objeto);


--
-- Name: venta venta_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.venta
    ADD CONSTRAINT venta_pkey PRIMARY KEY (id_venta);


--
-- Name: idx_af_mov; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_af_mov ON public.aplicacion_financiera USING btree (id_movimiento_financiero);


--
-- Name: idx_af_obl; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_af_obl ON public.aplicacion_financiera USING btree (id_obligacion_financiera);


--
-- Name: idx_ajuste_alquiler_uid_global; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ajuste_alquiler_uid_global ON public.ajuste_alquiler USING btree (uid_global);


--
-- Name: idx_ajuste_contrato; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ajuste_contrato ON public.ajuste_alquiler USING btree (id_contrato_alquiler);


--
-- Name: idx_aplicacion_financiera_uid_global; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_aplicacion_financiera_uid_global ON public.aplicacion_financiera USING btree (uid_global);


--
-- Name: idx_archivo_digital_uid_global; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_archivo_digital_uid_global ON public.archivo_digital USING btree (uid_global);


--
-- Name: idx_archivo_docv; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_archivo_docv ON public.archivo_digital USING btree (id_documento_version);


--
-- Name: idx_aud_entidad; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_aud_entidad ON public.evento_auditoria USING btree (tipo_entidad, id_entidad);


--
-- Name: idx_ca_cartera; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ca_cartera ON public.contrato_alquiler USING btree (id_cartera_locativa);


--
-- Name: idx_ca_contrato_anterior; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ca_contrato_anterior ON public.contrato_alquiler USING btree (id_contrato_anterior);


--
-- Name: uq_ca_reserva_activa; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_ca_reserva_activa ON public.contrato_alquiler (id_reserva_locativa)
    WHERE id_reserva_locativa IS NOT NULL AND deleted_at IS NULL;


--
-- Name: idx_cartera_locativa_uid_global; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_cartera_locativa_uid_global ON public.cartera_locativa USING btree (uid_global);


--
-- Name: idx_cea_contrato; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_cea_contrato ON public.condicion_economica_alquiler USING btree (id_contrato_alquiler);


--
-- Name: idx_cesion_uid_global; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_cesion_uid_global ON public.cesion USING btree (uid_global);


--
-- Name: idx_cesion_venta; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_cesion_venta ON public.cesion USING btree (id_venta);


--
-- Name: idx_cliente_comprador_persona; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_cliente_comprador_persona ON public.cliente_comprador USING btree (id_persona);


--
-- Name: idx_cliente_comprador_uid_global; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_cliente_comprador_uid_global ON public.cliente_comprador USING btree (uid_global);


--
-- Name: idx_co_obl; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_co_obl ON public.composicion_obligacion USING btree (id_obligacion_financiera);


--
-- Name: idx_co_concepto; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_co_concepto ON public.composicion_obligacion USING btree (id_concepto_financiero);


--
-- Name: idx_composicion_obligacion_deleted_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_composicion_obligacion_deleted_at ON public.composicion_obligacion USING btree (deleted_at);


--
-- Name: idx_concepto_financiero_codigo; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_concepto_financiero_codigo ON public.concepto_financiero USING btree (codigo_concepto_financiero);


--
-- Name: idx_concepto_financiero_deleted_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_concepto_financiero_deleted_at ON public.concepto_financiero USING btree (deleted_at);


--
-- Name: idx_col_contrato; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_col_contrato ON public.contrato_objeto_locativo USING btree (id_contrato_alquiler);


--
-- Name: idx_composicion_obligacion_uid_global; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_composicion_obligacion_uid_global ON public.composicion_obligacion USING btree (uid_global);


--
-- Name: idx_concepto_financiero_uid_global; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_concepto_financiero_uid_global ON public.concepto_financiero USING btree (uid_global);


--
-- Name: idx_conciliacion_bancaria_uid_global; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_conciliacion_bancaria_uid_global ON public.conciliacion_bancaria USING btree (uid_global);


--
-- Name: idx_condicion_economica_alquiler_uid_global; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_condicion_economica_alquiler_uid_global ON public.condicion_economica_alquiler USING btree (uid_global);


--
-- Name: idx_conflicto_entidad; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_conflicto_entidad ON public.conflicto_sincronizacion USING btree (tipo_entidad, id_entidad);


--
-- Name: idx_conflicto_uid_entidad; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_conflicto_uid_entidad ON public.conflicto_sincronizacion USING btree (uid_entidad);


--
-- Name: idx_contrato_alquiler_uid_global; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_contrato_alquiler_uid_global ON public.contrato_alquiler USING btree (uid_global);


--
-- Name: idx_contrato_objeto_locativo_uid_global; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_contrato_objeto_locativo_uid_global ON public.contrato_objeto_locativo USING btree (uid_global);


--
-- Name: idx_cred_usuario; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_cred_usuario ON public.credencial_usuario USING btree (id_usuario);


--
-- Name: idx_cuenta_financiera_uid_global; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_cuenta_financiera_uid_global ON public.cuenta_financiera USING btree (uid_global);


--
-- Name: idx_de_doc; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_de_doc ON public.documento_entidad USING btree (id_documento_logico);


--
-- Name: idx_de_polimorfico; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_de_polimorfico ON public.documento_entidad USING btree (tipo_entidad, id_entidad);


--
-- Name: idx_desarrollo_estado; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_desarrollo_estado ON public.desarrollo USING btree (estado_desarrollo);


--
-- Name: idx_desarrollo_sucursal_desarrollo; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_desarrollo_sucursal_desarrollo ON public.desarrollo_sucursal USING btree (id_desarrollo);


--
-- Name: idx_desarrollo_sucursal_sucursal; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_desarrollo_sucursal_sucursal ON public.desarrollo_sucursal USING btree (id_sucursal);


--
-- Name: idx_desarrollo_sucursal_uid_global; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_desarrollo_sucursal_uid_global ON public.desarrollo_sucursal USING btree (uid_global);


--
-- Name: idx_desarrollo_uid_global; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_desarrollo_uid_global ON public.desarrollo USING btree (uid_global);


--
-- Name: idx_detalle_conciliacion_uid_global; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_detalle_conciliacion_uid_global ON public.detalle_conciliacion USING btree (uid_global);


--
-- Name: idx_disp_inmueble; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_disp_inmueble ON public.disponibilidad USING btree (id_inmueble);


--
-- Name: idx_disp_unidad; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_disp_unidad ON public.disponibilidad USING btree (id_unidad_funcional);


--
-- Name: idx_disponibilidad_uid_global; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_disponibilidad_uid_global ON public.disponibilidad USING btree (uid_global);


--
-- Name: idx_doc_tipo; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_doc_tipo ON public.documento_logico USING btree (id_tipo_documental);


--
-- Name: idx_documento_entidad_uid_global; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_documento_entidad_uid_global ON public.documento_entidad USING btree (uid_global);


--
-- Name: idx_documento_logico_uid_global; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_documento_logico_uid_global ON public.documento_logico USING btree (uid_global);


--
-- Name: idx_documento_version_uid_global; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_documento_version_uid_global ON public.documento_version USING btree (uid_global);


--
-- Name: idx_docv_doc; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_docv_doc ON public.documento_version USING btree (id_documento_logico);


--
-- Name: idx_edificacion_inmueble; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_edificacion_inmueble ON public.edificacion USING btree (id_inmueble);


--
-- Name: idx_edificacion_uid_global; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_edificacion_uid_global ON public.edificacion USING btree (uid_global);


--
-- Name: idx_edificacion_unidad; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_edificacion_unidad ON public.edificacion USING btree (id_unidad_funcional);


--
-- Name: idx_emision_numeracion_uid_global; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_emision_numeracion_uid_global ON public.emision_numeracion USING btree (uid_global);


--
-- Name: idx_en_polimorfico; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_en_polimorfico ON public.emision_numeracion USING btree (tipo_entidad, id_entidad);


--
-- Name: idx_en_serie; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_en_serie ON public.emision_numeracion USING btree (id_numerador_serie);


--
-- Name: idx_entrega_restitucion_inmueble_uid_global; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_entrega_restitucion_inmueble_uid_global ON public.entrega_restitucion_inmueble USING btree (uid_global);


--
-- Name: uq_entrega_locativa_contrato; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_entrega_locativa_contrato
    ON public.entrega_locativa (id_contrato_alquiler)
    WHERE deleted_at IS NULL;


--
-- Name: idx_escritura_venta; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_escritura_venta ON public.escrituracion USING btree (id_venta);


--
-- Name: idx_escrituracion_uid_global; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_escrituracion_uid_global ON public.escrituracion USING btree (uid_global);


--
-- Name: idx_outbox_event_status_pending; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_outbox_event_status_pending ON public.outbox_event USING btree (status, published_at, occurred_at);

CREATE UNIQUE INDEX uq_outbox_event_id ON public.outbox_event (event_id);


--
-- Name: idx_ev_num; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ev_num ON public.evento_numeracion USING btree (id_emision_numeracion);


--
-- Name: idx_evento_numeracion_uid_global; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_evento_numeracion_uid_global ON public.evento_numeracion USING btree (uid_global);


--
-- Name: idx_factura_servicio_deleted_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_factura_servicio_deleted_at ON public.factura_servicio USING btree (deleted_at);


--
-- Name: idx_factura_servicio_estado; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_factura_servicio_estado ON public.factura_servicio USING btree (estado_factura_servicio);


--
-- Name: idx_factura_servicio_fecha_vencimiento; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_factura_servicio_fecha_vencimiento ON public.factura_servicio USING btree (fecha_vencimiento);


--
-- Name: idx_factura_servicio_id_inmueble; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_factura_servicio_id_inmueble ON public.factura_servicio USING btree (id_inmueble);


--
-- Name: idx_factura_servicio_id_servicio; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_factura_servicio_id_servicio ON public.factura_servicio USING btree (id_servicio);


--
-- Name: idx_factura_servicio_id_unidad_funcional; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_factura_servicio_id_unidad_funcional ON public.factura_servicio USING btree (id_unidad_funcional);


--
-- Name: idx_factura_servicio_uid_global; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_factura_servicio_uid_global ON public.factura_servicio USING btree (uid_global);


--
-- Name: idx_ic_venta; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ic_venta ON public.instrumento_compraventa USING btree (id_venta);


--
-- Name: idx_inmueble_desarrollo; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_inmueble_desarrollo ON public.inmueble USING btree (id_desarrollo);


--
-- Name: idx_inmueble_servicio_uid_global; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_inmueble_servicio_uid_global ON public.inmueble_servicio USING btree (uid_global);


--
-- Name: idx_inmueble_sucursal_inmueble; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_inmueble_sucursal_inmueble ON public.inmueble_sucursal USING btree (id_inmueble);


--
-- Name: idx_inmueble_sucursal_sucursal; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_inmueble_sucursal_sucursal ON public.inmueble_sucursal USING btree (id_sucursal);


--
-- Name: idx_inmueble_sucursal_uid_global; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_inmueble_sucursal_uid_global ON public.inmueble_sucursal USING btree (uid_global);


--
-- Name: idx_inmueble_uid_global; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_inmueble_uid_global ON public.inmueble USING btree (uid_global);


--
-- Name: idx_instalacion_estado; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_instalacion_estado ON public.instalacion USING btree (estado_instalacion);


--
-- Name: idx_instalacion_sucursal; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_instalacion_sucursal ON public.instalacion USING btree (id_sucursal);


--
-- Name: idx_instalacion_sucursal_estado; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_instalacion_sucursal_estado ON public.instalacion USING btree (id_sucursal, estado_instalacion);


--
-- Name: idx_instalacion_uid_global; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_instalacion_uid_global ON public.instalacion USING btree (uid_global);


--
-- Name: idx_instrumento_compraventa_uid_global; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_instrumento_compraventa_uid_global ON public.instrumento_compraventa USING btree (uid_global);


--
-- Name: idx_instrumento_objeto_uid_global; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_instrumento_objeto_uid_global ON public.instrumento_objeto_inmobiliario USING btree (uid_global);


--
-- Name: idx_io_instrumento; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_io_instrumento ON public.instrumento_objeto_inmobiliario USING btree (id_instrumento_compraventa);


--
-- Name: idx_lock_logico_entidad; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_lock_logico_entidad ON public.lock_logico USING btree (tipo_entidad, uid_entidad);


--
-- Name: idx_lock_logico_estado; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_lock_logico_estado ON public.lock_logico USING btree (estado_lock);


--
-- Name: idx_mod_contrato; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_mod_contrato ON public.modificacion_locativa USING btree (id_contrato_alquiler);


--
-- Name: idx_modificacion_locativa_uid_global; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_modificacion_locativa_uid_global ON public.modificacion_locativa USING btree (uid_global);


--
-- Name: idx_movimiento_financiero_uid_global; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_movimiento_financiero_uid_global ON public.movimiento_financiero USING btree (uid_global);


--
-- Name: idx_movimiento_tesoreria_uid_global; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_movimiento_tesoreria_uid_global ON public.movimiento_tesoreria USING btree (uid_global);


--
-- Name: idx_ns_numerador; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ns_numerador ON public.numerador_serie USING btree (id_numerador_documental);


--
-- Name: idx_ns_sucursal; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ns_sucursal ON public.numerador_serie USING btree (id_sucursal);


--
-- Name: idx_numerador_documental_uid_global; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_numerador_documental_uid_global ON public.numerador_documental USING btree (uid_global);


--
-- Name: idx_numerador_serie_uid_global; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_numerador_serie_uid_global ON public.numerador_serie USING btree (uid_global);


--
-- Name: idx_obl_rg; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_obl_rg ON public.obligacion_financiera USING btree (id_relacion_generadora);


--
-- Name: idx_obligacion_financiera_deleted_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_obligacion_financiera_deleted_at ON public.obligacion_financiera USING btree (deleted_at);


--
-- Name: idx_obligacion_financiera_estado; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_obligacion_financiera_estado ON public.obligacion_financiera USING btree (estado_obligacion);


--
-- Name: idx_obligacion_financiera_fecha_vencimiento; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_obligacion_financiera_fecha_vencimiento ON public.obligacion_financiera USING btree (fecha_vencimiento);


--
-- Name: idx_obligacion_financiera_reemplazada; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_obligacion_financiera_reemplazada ON public.obligacion_financiera USING btree (id_obligacion_reemplazada);


--
-- Name: idx_obligacion_financiera_reemplazante; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_obligacion_financiera_reemplazante ON public.obligacion_financiera USING btree (id_obligacion_reemplazante);


--
-- Name: idx_obligacion_financiera_uid_global; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_obligacion_financiera_uid_global ON public.obligacion_financiera USING btree (uid_global);


--
-- Name: idx_obligacion_obligado_uid_global; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_obligacion_obligado_uid_global ON public.obligacion_obligado USING btree (uid_global);


--
-- Name: idx_oc_inmueble; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_oc_inmueble ON public.ocupacion USING btree (id_inmueble);


--
-- Name: idx_oc_unidad; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_oc_unidad ON public.ocupacion USING btree (id_unidad_funcional);


--
-- Name: idx_ocupacion_uid_global; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ocupacion_uid_global ON public.ocupacion USING btree (uid_global);


--
-- Name: idx_oo_obl; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_oo_obl ON public.obligacion_obligado USING btree (id_obligacion_financiera);


--
-- Name: idx_oo_persona; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_oo_persona ON public.obligacion_obligado USING btree (id_persona);


--
-- Name: idx_pcont_persona; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_pcont_persona ON public.persona_contacto USING btree (id_persona);


--
-- Name: idx_pd_persona; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_pd_persona ON public.persona_documento USING btree (id_persona);


--
-- Name: idx_pdom_persona; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_pdom_persona ON public.persona_domicilio USING btree (id_persona);


--
-- Name: idx_persona_contacto_uid_global; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_persona_contacto_uid_global ON public.persona_contacto USING btree (uid_global);


--
-- Name: idx_persona_documento_uid_global; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_persona_documento_uid_global ON public.persona_documento USING btree (uid_global);


--
-- Name: idx_persona_domicilio_uid_global; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_persona_domicilio_uid_global ON public.persona_domicilio USING btree (uid_global);


--
-- Name: idx_persona_relacion_uid_global; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_persona_relacion_uid_global ON public.persona_relacion USING btree (uid_global);


--
-- Name: idx_persona_uid_global; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_persona_uid_global ON public.persona USING btree (uid_global);


--
-- Name: idx_pr_destino; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_pr_destino ON public.persona_relacion USING btree (id_persona_destino);


--
-- Name: idx_pr_origen; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_pr_origen ON public.persona_relacion USING btree (id_persona_origen);


--
-- Name: idx_relacion_generadora_uid_global; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_relacion_generadora_uid_global ON public.relacion_generadora USING btree (uid_global);


--
-- Name: idx_relacion_persona_rol_uid_global; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_relacion_persona_rol_uid_global ON public.relacion_persona_rol USING btree (uid_global);


--
-- Name: idx_rep_representado; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_rep_representado ON public.representacion_poder USING btree (id_persona_representado);


--
-- Name: idx_rep_representante; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_rep_representante ON public.representacion_poder USING btree (id_persona_representante);


--
-- Name: idx_representacion_poder_uid_global; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_representacion_poder_uid_global ON public.representacion_poder USING btree (uid_global);


--
-- Name: idx_resc_loc_contrato; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_resc_loc_contrato ON public.rescision_finalizacion_alquiler USING btree (id_contrato_alquiler);


--
-- Name: idx_rescision_finalizacion_alquiler_uid_global; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_rescision_finalizacion_alquiler_uid_global ON public.rescision_finalizacion_alquiler USING btree (uid_global);


--
-- Name: idx_rescision_venta_id_venta; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_rescision_venta_id_venta ON public.rescision_venta USING btree (id_venta);


--
-- Name: idx_rescision_venta_uid_global; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_rescision_venta_uid_global ON public.rescision_venta USING btree (uid_global);


--
-- Name: idx_reserva_locativa_uid_global; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_reserva_locativa_uid_global ON public.reserva_locativa USING btree (uid_global);


--
-- Name: idx_reserva_venta_uid_global; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_reserva_venta_uid_global ON public.reserva_venta USING btree (uid_global);


--
-- Name: idx_rg_origen; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_rg_origen ON public.relacion_generadora USING btree (tipo_origen, id_origen);


--
-- Name: idx_rl_solicitud; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_rl_solicitud ON public.reserva_locativa USING btree (id_solicitud_alquiler);


--
-- Name: idx_rol_participacion_uid_global; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_rol_participacion_uid_global ON public.rol_participacion USING btree (uid_global);


--
-- Name: idx_rpr_persona; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_rpr_persona ON public.relacion_persona_rol USING btree (id_persona);


--
-- Name: idx_rpr_polimorfico; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_rpr_polimorfico ON public.relacion_persona_rol USING btree (tipo_relacion, id_relacion);


--
-- Name: idx_rpr_rol; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_rpr_rol ON public.relacion_persona_rol USING btree (id_rol_participacion);


--
-- Name: idx_servicio_uid_global; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_servicio_uid_global ON public.servicio USING btree (uid_global);


--
-- Name: idx_sesion_usuario; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_sesion_usuario ON public.sesion_usuario USING btree (id_usuario);


--
-- Name: idx_solicitud_alquiler_uid_global; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_solicitud_alquiler_uid_global ON public.solicitud_alquiler USING btree (uid_global);


--
-- Name: idx_sucursal_estado; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_sucursal_estado ON public.sucursal USING btree (estado_sucursal);


--
-- Name: idx_sucursal_uid_global; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_sucursal_uid_global ON public.sucursal USING btree (uid_global);


--
-- Name: idx_tipo_documental_uid_global; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_tipo_documental_uid_global ON public.tipo_documental USING btree (uid_global);


--
-- Name: idx_ts_inmueble; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ts_inmueble ON public.inmueble_servicio USING btree (id_inmueble);


--
-- Name: idx_ts_servicio; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ts_servicio ON public.inmueble_servicio USING btree (id_servicio);


--
-- Name: idx_ufs_servicio; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ufs_servicio ON public.unidad_funcional_servicio USING btree (id_servicio);


--
-- Name: idx_ufs_uid_global; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ufs_uid_global ON public.unidad_funcional_servicio USING btree (uid_global);


--
-- Name: idx_ufs_unidad; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_ufs_unidad ON public.unidad_funcional_servicio USING btree (id_unidad_funcional);


--
-- Name: idx_unidad_funcional_uid_global; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_unidad_funcional_uid_global ON public.unidad_funcional USING btree (uid_global);


--
-- Name: idx_unidad_inmueble; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_unidad_inmueble ON public.unidad_funcional USING btree (id_inmueble);


--
-- Name: idx_up_persona; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_up_persona ON public.usuario_persona USING btree (id_persona);


--
-- Name: idx_up_usuario; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_up_usuario ON public.usuario_persona USING btree (id_usuario);


--
-- Name: idx_us_sucursal; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_us_sucursal ON public.usuario_sucursal USING btree (id_sucursal);


--
-- Name: idx_us_usuario; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_us_usuario ON public.usuario_sucursal USING btree (id_usuario);


--
-- Name: idx_venta_objeto_uid_global; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_venta_objeto_uid_global ON public.venta_objeto_inmobiliario USING btree (uid_global);


--
-- Name: idx_venta_reserva; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_venta_reserva ON public.venta USING btree (id_reserva_venta);


--
-- Name: idx_venta_uid_global; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_venta_uid_global ON public.venta USING btree (uid_global);


--
-- Name: idx_vo_venta; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_vo_venta ON public.venta_objeto_inmobiliario USING btree (id_venta);


--
-- Name: ix_aplicacion_financiera_composicion; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_aplicacion_financiera_composicion ON public.aplicacion_financiera USING btree (id_composicion_obligacion);


--
-- Name: ix_aplicacion_financiera_movimiento_obligacion; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_aplicacion_financiera_movimiento_obligacion ON public.aplicacion_financiera USING btree (id_movimiento_financiero, id_obligacion_financiera);


--
-- Name: ix_archivo_digital_docv_hash; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_archivo_digital_docv_hash ON public.archivo_digital USING btree (id_documento_version, hash_archivo);


--
-- Name: ix_cliente_comprador_estado; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_cliente_comprador_estado ON public.cliente_comprador USING btree (estado_cliente_comprador);


--
-- Name: ix_cliente_comprador_version_registro; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_cliente_comprador_version_registro ON public.cliente_comprador USING btree (version_registro);


--
-- Name: ix_composicion_obligacion_obligacion_concepto; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_composicion_obligacion_obligacion_concepto ON public.composicion_obligacion USING btree (id_obligacion_financiera, id_concepto_financiero);


--
-- Name: ix_conciliacion_bancaria_cuenta_periodo; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_conciliacion_bancaria_cuenta_periodo ON public.conciliacion_bancaria USING btree (id_cuenta_financiera, fecha_conciliacion);


--
-- Name: ix_condicion_economica_alquiler_vigencia; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_condicion_economica_alquiler_vigencia ON public.condicion_economica_alquiler USING btree (id_contrato_alquiler, fecha_desde, fecha_hasta);


--
-- Name: ix_conflicto_sincronizacion_estado_fecha; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_conflicto_sincronizacion_estado_fecha ON public.conflicto_sincronizacion USING btree (estado_conflicto, fecha_detectado);


--
-- Name: ix_contrato_alquiler_version_registro; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_contrato_alquiler_version_registro ON public.contrato_alquiler USING btree (version_registro);


--
-- Name: ix_credencial_usuario_estado; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_credencial_usuario_estado ON public.credencial_usuario USING btree (id_usuario, estado_credencial);


--
-- Name: ix_desarrollo_sucursal_vigencia; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_desarrollo_sucursal_vigencia ON public.desarrollo_sucursal USING btree (id_desarrollo, id_sucursal, fecha_desde, fecha_hasta);


--
-- Name: ix_desarrollo_version_registro; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_desarrollo_version_registro ON public.desarrollo USING btree (version_registro);


--
-- Name: ix_detalle_conciliacion_movimiento; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_detalle_conciliacion_movimiento ON public.detalle_conciliacion USING btree (id_movimiento_tesoreria);


--
-- Name: ix_disponibilidad_inmueble_vigencia; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_disponibilidad_inmueble_vigencia ON public.disponibilidad USING btree (id_inmueble, fecha_desde, fecha_hasta);


--
-- Name: ix_disponibilidad_unidad_vigencia; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_disponibilidad_unidad_vigencia ON public.disponibilidad USING btree (id_unidad_funcional, fecha_desde, fecha_hasta);


--
-- Name: ix_disponibilidad_version_registro; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_disponibilidad_version_registro ON public.disponibilidad USING btree (version_registro);


--
-- Name: ix_documento_entidad_tipo_entidad; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_documento_entidad_tipo_entidad ON public.documento_entidad USING btree (tipo_entidad, id_entidad);


--
-- Name: ix_documento_logico_tipo_estado; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_documento_logico_tipo_estado ON public.documento_logico USING btree (id_tipo_documental, estado_documento);


--
-- Name: ix_documento_logico_version_registro; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_documento_logico_version_registro ON public.documento_logico USING btree (version_registro);


--
-- Name: ix_documento_version_doc_actual; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_documento_version_doc_actual ON public.documento_version USING btree (id_documento_logico, es_version_actual);


--
-- Name: ix_documento_version_doc_estado; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_documento_version_doc_estado ON public.documento_version USING btree (id_documento_logico, estado_version);


--
-- Name: ix_emision_numeracion_estado_fecha; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_emision_numeracion_estado_fecha ON public.emision_numeracion USING btree (estado_emision, fecha_emision);


--
-- Name: ix_evento_auditoria_instalacion_fecha; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_evento_auditoria_instalacion_fecha ON public.evento_auditoria USING btree (id_instalacion, fecha_hora_evento);


--
-- Name: ix_evento_auditoria_op_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_evento_auditoria_op_id ON public.operacion_auditoria USING btree (op_id);


--
-- Name: ix_evento_auditoria_sucursal_fecha; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_evento_auditoria_sucursal_fecha ON public.evento_auditoria USING btree (id_sucursal, fecha_hora_evento);


--
-- Name: ix_evento_auditoria_usuario_fecha; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_evento_auditoria_usuario_fecha ON public.evento_auditoria USING btree (id_usuario, fecha_hora_evento);


--
-- Name: ix_evento_numeracion_tipo_fecha; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_evento_numeracion_tipo_fecha ON public.evento_numeracion USING btree (tipo_evento, fecha_evento);


--
-- Name: ix_historial_acceso_instalacion_fecha; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_historial_acceso_instalacion_fecha ON public.historial_acceso USING btree (id_instalacion_contexto, fecha_hora_evento);


--
-- Name: ix_historial_acceso_usuario_fecha; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_historial_acceso_usuario_fecha ON public.historial_acceso USING btree (id_usuario, fecha_hora_evento);


--
-- Name: ix_historial_parametro_parametro_fecha; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_historial_parametro_parametro_fecha ON public.historial_parametro USING btree (id_parametro_sistema, fecha_hora_cambio);


--
-- Name: ix_inmueble_sucursal_vigencia; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_inmueble_sucursal_vigencia ON public.inmueble_sucursal USING btree (id_inmueble, id_sucursal, fecha_desde, fecha_hasta);


--
-- Name: ix_inmueble_version_registro; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_inmueble_version_registro ON public.inmueble USING btree (version_registro);


--
-- Name: ix_item_catalogo_catalogo_estado; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_item_catalogo_catalogo_estado ON public.item_catalogo USING btree (id_catalogo_maestro, estado_item_catalogo);


--
-- Name: ix_jerarquia_item_catalogo_hijo; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_jerarquia_item_catalogo_hijo ON public.jerarquia_item_catalogo USING btree (id_item_catalogo_hijo);


--
-- Name: ix_jerarquia_item_catalogo_padre; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_jerarquia_item_catalogo_padre ON public.jerarquia_item_catalogo USING btree (id_item_catalogo_padre);


--
-- Name: ix_lock_logico_op_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_lock_logico_op_id ON public.lock_logico USING btree (op_id);


--
-- Name: ix_movimiento_financiero_fecha_estado; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_movimiento_financiero_fecha_estado ON public.movimiento_financiero USING btree (fecha_movimiento, estado_movimiento);


--
-- Name: ix_movimiento_tesoreria_cuenta_fecha; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_movimiento_tesoreria_cuenta_fecha ON public.movimiento_tesoreria USING btree (id_cuenta_financiera_origen, fecha_movimiento);


--
-- Name: ix_numerador_serie_numerador_estado; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_numerador_serie_numerador_estado ON public.numerador_serie USING btree (id_numerador_documental, estado_serie);


--
-- Name: ix_objeto_auditado_entidad; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_objeto_auditado_entidad ON public.objeto_auditado USING btree (tipo_entidad, id_entidad);


--
-- Name: ix_obligacion_financiera_estado_vencimiento; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_obligacion_financiera_estado_vencimiento ON public.obligacion_financiera USING btree (estado_obligacion, fecha_vencimiento);


--
-- Name: ix_obligacion_financiera_version_registro; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_obligacion_financiera_version_registro ON public.obligacion_financiera USING btree (version_registro);


--
-- Name: ix_obligacion_obligado_persona_obligacion; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_obligacion_obligado_persona_obligacion ON public.obligacion_obligado USING btree (id_persona, id_obligacion_financiera);


--
-- Name: ix_ocupacion_inmueble_vigencia; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_ocupacion_inmueble_vigencia ON public.ocupacion USING btree (id_inmueble, fecha_desde, fecha_hasta);


--
-- Name: ix_ocupacion_unidad_vigencia; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_ocupacion_unidad_vigencia ON public.ocupacion USING btree (id_unidad_funcional, fecha_desde, fecha_hasta);


--
-- Name: ix_ocupacion_version_registro; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_ocupacion_version_registro ON public.ocupacion USING btree (version_registro);


--
-- Name: ix_persona_apellido_nombre; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_persona_apellido_nombre ON public.persona USING btree (apellido, nombre);


--
-- Name: ix_persona_contacto_persona_vigencia; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_persona_contacto_persona_vigencia ON public.persona_contacto USING btree (id_persona, fecha_desde, fecha_hasta);


--
-- Name: ix_persona_contacto_valor; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_persona_contacto_valor ON public.persona_contacto USING btree (valor_contacto);


--
-- Name: ix_persona_contacto_version_registro; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_persona_contacto_version_registro ON public.persona_contacto USING btree (version_registro);


--
-- Name: ix_persona_deleted_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_persona_deleted_at ON public.persona USING btree (deleted_at);


--
-- Name: ix_persona_documento_persona_vigencia; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_persona_documento_persona_vigencia ON public.persona_documento USING btree (id_persona, fecha_desde, fecha_hasta);


--
-- Name: ix_persona_documento_tipo_numero; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_persona_documento_tipo_numero ON public.persona_documento USING btree (tipo_documento_persona, numero_documento);


--
-- Name: ix_persona_documento_version_registro; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_persona_documento_version_registro ON public.persona_documento USING btree (version_registro);


--
-- Name: ix_persona_domicilio_persona_vigencia; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_persona_domicilio_persona_vigencia ON public.persona_domicilio USING btree (id_persona, fecha_desde, fecha_hasta);


--
-- Name: ix_persona_domicilio_version_registro; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_persona_domicilio_version_registro ON public.persona_domicilio USING btree (version_registro);


--
-- Name: ix_persona_estado; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_persona_estado ON public.persona USING btree (estado_persona);


--
-- Name: ix_persona_op_id_alta; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_persona_op_id_alta ON public.persona USING btree (op_id_alta);


--
-- Name: ix_persona_op_id_ultima_modificacion; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_persona_op_id_ultima_modificacion ON public.persona USING btree (op_id_ultima_modificacion);


--
-- Name: ix_persona_razon_social; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_persona_razon_social ON public.persona USING btree (razon_social);


--
-- Name: ix_persona_relacion_destino_vigencia; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_persona_relacion_destino_vigencia ON public.persona_relacion USING btree (id_persona_destino, tipo_relacion, fecha_desde, fecha_hasta);


--
-- Name: ix_persona_relacion_origen_vigencia; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_persona_relacion_origen_vigencia ON public.persona_relacion USING btree (id_persona_origen, tipo_relacion, fecha_desde, fecha_hasta);


--
-- Name: ix_persona_relacion_version_registro; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_persona_relacion_version_registro ON public.persona_relacion USING btree (version_registro);


--
-- Name: ix_persona_tipo; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_persona_tipo ON public.persona USING btree (tipo_persona);


--
-- Name: ix_persona_updated_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_persona_updated_at ON public.persona USING btree (updated_at);


--
-- Name: ix_persona_version_registro; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_persona_version_registro ON public.persona USING btree (version_registro);


--
-- Name: ix_relacion_generadora_version_registro; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_relacion_generadora_version_registro ON public.relacion_generadora USING btree (version_registro);


--
-- Name: ix_relacion_persona_rol_persona_rol_vigencia; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_relacion_persona_rol_persona_rol_vigencia ON public.relacion_persona_rol USING btree (id_persona, id_rol_participacion, fecha_desde, fecha_hasta);


--
-- Name: ix_relacion_persona_rol_version_registro; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_relacion_persona_rol_version_registro ON public.relacion_persona_rol USING btree (version_registro);


--
-- Name: ix_representacion_poder_representado_vigencia; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_representacion_poder_representado_vigencia ON public.representacion_poder USING btree (id_persona_representado, fecha_desde, fecha_hasta);


--
-- Name: ix_representacion_poder_representante_vigencia; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_representacion_poder_representante_vigencia ON public.representacion_poder USING btree (id_persona_representante, fecha_desde, fecha_hasta);


--
-- Name: ix_representacion_poder_version_registro; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_representacion_poder_version_registro ON public.representacion_poder USING btree (version_registro);


--
-- Name: ix_sesion_usuario_instalacion_estado_fecha; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_sesion_usuario_instalacion_estado_fecha ON public.sesion_usuario USING btree (id_instalacion_origen, estado_sesion, fecha_hora_inicio);


--
-- Name: ix_sinc_operacion_entidad; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_sinc_operacion_entidad ON public.sincronizacion_operacion USING btree (entidad_principal, id_entidad_principal);


--
-- Name: ix_sinc_operacion_estado_fecha; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_sinc_operacion_estado_fecha ON public.sincronizacion_operacion USING btree (estado_operacion, fecha_hora_operacion);


--
-- Name: ix_sinc_operacion_op_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_sinc_operacion_op_id ON public.sincronizacion_operacion USING btree (op_id);


--
-- Name: ix_sinc_operacion_paquete; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_sinc_operacion_paquete ON public.sincronizacion_operacion USING btree (id_sincronizacion_paquete);


--
-- Name: ix_sinc_operacion_uid_entidad; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_sinc_operacion_uid_entidad ON public.sincronizacion_operacion USING btree (uid_entidad);


--
-- Name: ix_sinc_paquete_estado; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_sinc_paquete_estado ON public.sincronizacion_paquete USING btree (estado_paquete);


--
-- Name: ix_sinc_paquete_fecha_generacion; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_sinc_paquete_fecha_generacion ON public.sincronizacion_paquete USING btree (fecha_hora_generacion);


--
-- Name: ix_sinc_paquete_instalacion_origen; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_sinc_paquete_instalacion_origen ON public.sincronizacion_paquete USING btree (id_instalacion_origen);


--
-- Name: ix_sinc_paquete_origen_fecha; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_sinc_paquete_origen_fecha ON public.sincronizacion_paquete USING btree (id_instalacion_origen, fecha_hora_generacion);


--
-- Name: ix_sinc_recepcion_estado_fecha; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_sinc_recepcion_estado_fecha ON public.sincronizacion_recepcion USING btree (estado_recepcion, fecha_hora_recepcion);


--
-- Name: ix_sinc_recepcion_instalacion; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_sinc_recepcion_instalacion ON public.sincronizacion_recepcion USING btree (id_instalacion_receptora);


--
-- Name: ix_sinc_recepcion_op_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_sinc_recepcion_op_id ON public.sincronizacion_recepcion USING btree (op_id);


--
-- Name: ix_unidad_funcional_version_registro; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_unidad_funcional_version_registro ON public.unidad_funcional USING btree (version_registro);


--
-- Name: ix_usuario_persona_vigencia; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_usuario_persona_vigencia ON public.usuario_persona USING btree (id_usuario, id_persona, fecha_desde, fecha_hasta);


--
-- Name: ix_usuario_rol_seguridad_vigencia; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_usuario_rol_seguridad_vigencia ON public.usuario_rol_seguridad USING btree (id_usuario, id_rol_seguridad, fecha_desde, fecha_hasta);


--
-- Name: ix_usuario_rol_sucursal_vigencia; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_usuario_rol_sucursal_vigencia ON public.usuario_rol_sucursal USING btree (id_usuario, id_rol_seguridad, id_sucursal, fecha_desde, fecha_hasta);


--
-- Name: ix_usuario_sucursal_vigencia; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_usuario_sucursal_vigencia ON public.usuario_sucursal USING btree (id_usuario, id_sucursal, fecha_desde, fecha_hasta);


--
-- Name: ix_valor_parametro_contexto_vigencia; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_valor_parametro_contexto_vigencia ON public.valor_parametro USING btree (id_parametro_sistema, id_sucursal, id_instalacion, fecha_desde, fecha_hasta);


--
-- Name: ix_valor_parametro_instalacion; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_valor_parametro_instalacion ON public.valor_parametro USING btree (id_instalacion);


--
-- Name: ix_valor_parametro_sucursal; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_valor_parametro_sucursal ON public.valor_parametro USING btree (id_sucursal);


--
-- Name: ix_venta_version_registro; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_venta_version_registro ON public.venta USING btree (version_registro);


--
-- Name: ux_cliente_comprador_persona_activa; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ux_cliente_comprador_persona_activa ON public.cliente_comprador USING btree (id_persona) WHERE (deleted_at IS NULL);


--
-- Name: ux_emision_numeracion_serie_numero; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ux_emision_numeracion_serie_numero ON public.emision_numeracion USING btree (id_numerador_serie, numero_emitido);


--
-- Name: ux_inmueble_servicio_activo; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ux_inmueble_servicio_activo ON public.inmueble_servicio USING btree (id_inmueble, id_servicio) WHERE (deleted_at IS NULL);


--
-- Name: ux_factura_servicio_activa_proveedor_numero; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ux_factura_servicio_activa_proveedor_numero ON public.factura_servicio USING btree (proveedor, numero_factura) WHERE (deleted_at IS NULL);


--
-- Name: ux_parametro_opcion_parametro_codigo; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ux_parametro_opcion_parametro_codigo ON public.parametro_opcion USING btree (id_parametro_sistema, codigo_opcion);


--
-- Name: ux_persona_contacto_principal_activo; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ux_persona_contacto_principal_activo ON public.persona_contacto USING btree (id_persona, tipo_contacto) WHERE ((es_principal = true) AND (deleted_at IS NULL));


--
-- Name: ux_persona_contacto_valor_activo; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ux_persona_contacto_valor_activo ON public.persona_contacto USING btree (tipo_contacto, valor_contacto, id_persona) WHERE (deleted_at IS NULL);


--
-- Name: ux_persona_documento_tipo_numero_activo; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ux_persona_documento_tipo_numero_activo ON public.persona_documento USING btree (tipo_documento_persona, numero_documento) WHERE (deleted_at IS NULL);


--
-- Name: ux_persona_domicilio_principal_activo; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ux_persona_domicilio_principal_activo ON public.persona_domicilio USING btree (id_persona) WHERE ((es_principal = true) AND (deleted_at IS NULL));


--
-- Name: ux_rol_seguridad_permiso; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ux_rol_seguridad_permiso ON public.rol_seguridad_permiso USING btree (id_rol_seguridad, id_permiso);


--
-- Name: aplicacion_financiera trg_aiud_aplicacion_financiera_refrescar_saldo_obligacion; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_aiud_aplicacion_financiera_refrescar_saldo_obligacion AFTER INSERT OR DELETE OR UPDATE ON public.aplicacion_financiera FOR EACH ROW EXECUTE FUNCTION public.trg_aplicacion_financiera_refrescar_saldo_obligacion();


--
-- Name: aplicacion_financiera trg_bi_aplicacion_financiera_core_ef; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_bi_aplicacion_financiera_core_ef BEFORE INSERT ON public.aplicacion_financiera FOR EACH ROW EXECUTE FUNCTION public.trg_core_ef_sync_defaults_insert();


--
-- Name: cliente_comprador trg_bi_cliente_comprador_core_ef; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_bi_cliente_comprador_core_ef BEFORE INSERT ON public.cliente_comprador FOR EACH ROW EXECUTE FUNCTION public.trg_core_ef_sync_defaults_insert();


--
-- Name: composicion_obligacion trg_bi_composicion_obligacion_core_ef; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_bi_composicion_obligacion_core_ef BEFORE INSERT ON public.composicion_obligacion FOR EACH ROW EXECUTE FUNCTION public.trg_core_ef_sync_defaults_insert();


--
-- Name: concepto_financiero trg_bi_concepto_financiero_core_ef; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_bi_concepto_financiero_core_ef BEFORE INSERT ON public.concepto_financiero FOR EACH ROW EXECUTE FUNCTION public.trg_core_ef_sync_defaults_insert();


--
-- Name: desarrollo trg_bi_desarrollo_core_ef; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_bi_desarrollo_core_ef BEFORE INSERT ON public.desarrollo FOR EACH ROW EXECUTE FUNCTION public.trg_core_ef_sync_defaults_insert();


--
-- Name: desarrollo_sucursal trg_bi_desarrollo_sucursal_core_ef; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_bi_desarrollo_sucursal_core_ef BEFORE INSERT ON public.desarrollo_sucursal FOR EACH ROW EXECUTE FUNCTION public.trg_core_ef_sync_defaults_insert();


--
-- Name: disponibilidad trg_bi_disponibilidad_core_ef; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_bi_disponibilidad_core_ef BEFORE INSERT ON public.disponibilidad FOR EACH ROW EXECUTE FUNCTION public.trg_core_ef_sync_defaults_insert();


--
-- Name: documento_entidad trg_bi_documento_entidad_core_ef; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_bi_documento_entidad_core_ef BEFORE INSERT ON public.documento_entidad FOR EACH ROW EXECUTE FUNCTION public.trg_core_ef_sync_defaults_insert();


--
-- Name: emision_numeracion trg_bi_emision_numeracion_core_ef; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_bi_emision_numeracion_core_ef BEFORE INSERT ON public.emision_numeracion FOR EACH ROW EXECUTE FUNCTION public.trg_core_ef_sync_defaults_insert();


--
-- Name: factura_servicio trg_bi_factura_servicio_core_ef; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_bi_factura_servicio_core_ef BEFORE INSERT ON public.factura_servicio FOR EACH ROW EXECUTE FUNCTION public.trg_core_ef_sync_defaults_insert();


--
-- Name: inmueble trg_bi_inmueble_core_ef; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_bi_inmueble_core_ef BEFORE INSERT ON public.inmueble FOR EACH ROW EXECUTE FUNCTION public.trg_core_ef_sync_defaults_insert();


--
-- Name: inmueble_sucursal trg_bi_inmueble_sucursal_core_ef; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_bi_inmueble_sucursal_core_ef BEFORE INSERT ON public.inmueble_sucursal FOR EACH ROW EXECUTE FUNCTION public.trg_core_ef_sync_defaults_insert();


--
-- Name: instalacion trg_bi_instalacion_core_ef; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_bi_instalacion_core_ef BEFORE INSERT ON public.instalacion FOR EACH ROW EXECUTE FUNCTION public.trg_core_ef_sync_defaults_insert();


--
-- Name: movimiento_financiero trg_bi_movimiento_financiero_core_ef; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_bi_movimiento_financiero_core_ef BEFORE INSERT ON public.movimiento_financiero FOR EACH ROW EXECUTE FUNCTION public.trg_core_ef_sync_defaults_insert();


--
-- Name: obligacion_financiera trg_bi_obligacion_financiera_core_ef; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_bi_obligacion_financiera_core_ef BEFORE INSERT ON public.obligacion_financiera FOR EACH ROW EXECUTE FUNCTION public.trg_core_ef_sync_defaults_insert();


--
-- Name: ocupacion trg_bi_ocupacion_core_ef; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_bi_ocupacion_core_ef BEFORE INSERT ON public.ocupacion FOR EACH ROW EXECUTE FUNCTION public.trg_core_ef_sync_defaults_insert();


--
-- Name: persona_contacto trg_bi_persona_contacto_core_ef; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_bi_persona_contacto_core_ef BEFORE INSERT ON public.persona_contacto FOR EACH ROW EXECUTE FUNCTION public.trg_core_ef_sync_defaults_insert();


--
-- Name: persona trg_bi_persona_core_ef; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_bi_persona_core_ef BEFORE INSERT ON public.persona FOR EACH ROW EXECUTE FUNCTION public.trg_core_ef_sync_defaults_insert();


--
-- Name: persona_documento trg_bi_persona_documento_core_ef; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_bi_persona_documento_core_ef BEFORE INSERT ON public.persona_documento FOR EACH ROW EXECUTE FUNCTION public.trg_core_ef_sync_defaults_insert();


--
-- Name: persona_domicilio trg_bi_persona_domicilio_core_ef; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_bi_persona_domicilio_core_ef BEFORE INSERT ON public.persona_domicilio FOR EACH ROW EXECUTE FUNCTION public.trg_core_ef_sync_defaults_insert();


--
-- Name: persona_relacion trg_bi_persona_relacion_core_ef; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_bi_persona_relacion_core_ef BEFORE INSERT ON public.persona_relacion FOR EACH ROW EXECUTE FUNCTION public.trg_core_ef_sync_defaults_insert();


--
-- Name: relacion_generadora trg_bi_relacion_generadora_core_ef; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_bi_relacion_generadora_core_ef BEFORE INSERT ON public.relacion_generadora FOR EACH ROW EXECUTE FUNCTION public.trg_core_ef_sync_defaults_insert();


--
-- Name: relacion_persona_rol trg_bi_relacion_persona_rol_core_ef; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_bi_relacion_persona_rol_core_ef BEFORE INSERT ON public.relacion_persona_rol FOR EACH ROW EXECUTE FUNCTION public.trg_core_ef_sync_defaults_insert();


--
-- Name: representacion_poder trg_bi_representacion_poder_core_ef; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_bi_representacion_poder_core_ef BEFORE INSERT ON public.representacion_poder FOR EACH ROW EXECUTE FUNCTION public.trg_core_ef_sync_defaults_insert();


--
-- Name: rol_participacion trg_bi_rol_participacion_core_ef; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_bi_rol_participacion_core_ef BEFORE INSERT ON public.rol_participacion FOR EACH ROW EXECUTE FUNCTION public.trg_core_ef_sync_defaults_insert();


--
-- Name: sucursal trg_bi_sucursal_core_ef; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_bi_sucursal_core_ef BEFORE INSERT ON public.sucursal FOR EACH ROW EXECUTE FUNCTION public.trg_core_ef_sync_defaults_insert();


--
-- Name: unidad_funcional trg_bi_unidad_funcional_core_ef; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_bi_unidad_funcional_core_ef BEFORE INSERT ON public.unidad_funcional FOR EACH ROW EXECUTE FUNCTION public.trg_core_ef_sync_defaults_insert();


--
-- Name: aplicacion_financiera trg_biu_aplicacion_financiera_validar_consistencia; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_biu_aplicacion_financiera_validar_consistencia BEFORE INSERT OR UPDATE ON public.aplicacion_financiera FOR EACH ROW EXECUTE FUNCTION public.trg_aplicacion_financiera_validar_consistencia();


--
-- Name: condicion_economica_alquiler trg_biu_condicion_economica_alquiler_no_solapada; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_biu_condicion_economica_alquiler_no_solapada BEFORE INSERT OR UPDATE ON public.condicion_economica_alquiler FOR EACH ROW EXECUTE FUNCTION public.trg_condicion_economica_alquiler_no_solapada();


--
-- Name: desarrollo_sucursal trg_biu_desarrollo_sucursal_no_solapada; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_biu_desarrollo_sucursal_no_solapada BEFORE INSERT OR UPDATE ON public.desarrollo_sucursal FOR EACH ROW EXECUTE FUNCTION public.trg_desarrollo_sucursal_no_solapada();


--
-- Name: disponibilidad trg_biu_disponibilidad_no_solapada; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_biu_disponibilidad_no_solapada BEFORE INSERT OR UPDATE ON public.disponibilidad FOR EACH ROW EXECUTE FUNCTION public.trg_disponibilidad_no_solapada();


--
-- Name: documento_entidad trg_biu_documento_entidad_polimorfica; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_biu_documento_entidad_polimorfica BEFORE INSERT OR UPDATE ON public.documento_entidad FOR EACH ROW EXECUTE FUNCTION public.trg_documento_entidad_polimorfica();


--
-- Name: emision_numeracion trg_biu_emision_numeracion_polimorfica; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_biu_emision_numeracion_polimorfica BEFORE INSERT OR UPDATE ON public.emision_numeracion FOR EACH ROW EXECUTE FUNCTION public.trg_emision_numeracion_polimorfica();


--
-- Name: factura_servicio trg_biu_factura_servicio_validar_asociacion; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_biu_factura_servicio_validar_asociacion BEFORE INSERT OR UPDATE ON public.factura_servicio FOR EACH ROW EXECUTE FUNCTION public.trg_factura_servicio_validar_asociacion();


--
-- Name: historial_acceso trg_biu_historial_acceso_instalacion_sucursal; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_biu_historial_acceso_instalacion_sucursal BEFORE INSERT OR UPDATE ON public.historial_acceso FOR EACH ROW EXECUTE FUNCTION public.trg_historial_acceso_instalacion_sucursal();


--
-- Name: historial_acceso trg_biu_historial_acceso_usuario_sesion; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_biu_historial_acceso_usuario_sesion BEFORE INSERT OR UPDATE ON public.historial_acceso FOR EACH ROW EXECUTE FUNCTION public.trg_historial_acceso_usuario_sesion();


--
-- Name: inmueble_sucursal trg_biu_inmueble_sucursal_no_solapada; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_biu_inmueble_sucursal_no_solapada BEFORE INSERT OR UPDATE ON public.inmueble_sucursal FOR EACH ROW EXECUTE FUNCTION public.trg_inmueble_sucursal_no_solapada();


--
-- Name: lock_logico trg_biu_lock_logico_no_solapado; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_biu_lock_logico_no_solapado BEFORE INSERT OR UPDATE ON public.lock_logico FOR EACH ROW EXECUTE FUNCTION public.trg_lock_logico_no_solapado();


--
-- Name: ocupacion trg_biu_ocupacion_no_solapada; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_biu_ocupacion_no_solapada BEFORE INSERT OR UPDATE ON public.ocupacion FOR EACH ROW EXECUTE FUNCTION public.trg_ocupacion_no_solapada();


--
-- Name: persona_contacto trg_biu_persona_contacto_no_solapado; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_biu_persona_contacto_no_solapado BEFORE INSERT OR UPDATE ON public.persona_contacto FOR EACH ROW EXECUTE FUNCTION public.trg_persona_contacto_no_solapado();


--
-- Name: persona_documento trg_biu_persona_documento_no_solapado; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_biu_persona_documento_no_solapado BEFORE INSERT OR UPDATE ON public.persona_documento FOR EACH ROW EXECUTE FUNCTION public.trg_persona_documento_no_solapado();


--
-- Name: persona_domicilio trg_biu_persona_domicilio_no_solapado; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_biu_persona_domicilio_no_solapado BEFORE INSERT OR UPDATE ON public.persona_domicilio FOR EACH ROW EXECUTE FUNCTION public.trg_persona_domicilio_no_solapado();


--
-- Name: persona_relacion trg_biu_persona_relacion_no_solapada; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_biu_persona_relacion_no_solapada BEFORE INSERT OR UPDATE ON public.persona_relacion FOR EACH ROW EXECUTE FUNCTION public.trg_persona_relacion_no_solapada();


--
-- Name: relacion_generadora trg_biu_relacion_generadora_polimorfica; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_biu_relacion_generadora_polimorfica BEFORE INSERT OR UPDATE ON public.relacion_generadora FOR EACH ROW EXECUTE FUNCTION public.trg_relacion_generadora_polimorfica();


--
-- Name: relacion_persona_rol trg_biu_relacion_persona_rol_no_solapada; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_biu_relacion_persona_rol_no_solapada BEFORE INSERT OR UPDATE ON public.relacion_persona_rol FOR EACH ROW EXECUTE FUNCTION public.trg_relacion_persona_rol_no_solapada();


--
-- Name: relacion_persona_rol trg_biu_relacion_persona_rol_polimorfica; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_biu_relacion_persona_rol_polimorfica BEFORE INSERT OR UPDATE ON public.relacion_persona_rol FOR EACH ROW EXECUTE FUNCTION public.trg_relacion_persona_rol_polimorfica();


--
-- Name: representacion_poder trg_biu_representacion_poder_no_solapada; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_biu_representacion_poder_no_solapada BEFORE INSERT OR UPDATE ON public.representacion_poder FOR EACH ROW EXECUTE FUNCTION public.trg_representacion_poder_no_solapada();


--
-- Name: sesion_usuario trg_biu_sesion_usuario_instalacion_sucursal; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_biu_sesion_usuario_instalacion_sucursal BEFORE INSERT OR UPDATE ON public.sesion_usuario FOR EACH ROW EXECUTE FUNCTION public.trg_sesion_usuario_instalacion_sucursal();


--
-- Name: sincronizacion_operacion trg_biu_sincronizacion_operacion_uid_vs_id; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_biu_sincronizacion_operacion_uid_vs_id BEFORE INSERT OR UPDATE ON public.sincronizacion_operacion FOR EACH ROW EXECUTE FUNCTION public.trg_sincronizacion_operacion_uid_vs_id();


--
-- Name: sincronizacion_paquete trg_biu_sincronizacion_paquete_instalacion_valida; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_biu_sincronizacion_paquete_instalacion_valida BEFORE INSERT OR UPDATE ON public.sincronizacion_paquete FOR EACH ROW EXECUTE FUNCTION public.trg_sincronizacion_paquete_instalacion_valida();


--
-- Name: sincronizacion_recepcion trg_biu_sincronizacion_recepcion_conflicto_consistente; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_biu_sincronizacion_recepcion_conflicto_consistente BEFORE INSERT OR UPDATE ON public.sincronizacion_recepcion FOR EACH ROW EXECUTE FUNCTION public.trg_sincronizacion_recepcion_conflicto_consistente();


--
-- Name: aplicacion_financiera trg_bu_aplicacion_financiera_core_ef; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_bu_aplicacion_financiera_core_ef BEFORE UPDATE ON public.aplicacion_financiera FOR EACH ROW EXECUTE FUNCTION public.trg_core_ef_sync_defaults_update();


--
-- Name: cliente_comprador trg_bu_cliente_comprador_core_ef; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_bu_cliente_comprador_core_ef BEFORE UPDATE ON public.cliente_comprador FOR EACH ROW EXECUTE FUNCTION public.trg_core_ef_sync_defaults_update();


--
-- Name: composicion_obligacion trg_bu_composicion_obligacion_core_ef; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_bu_composicion_obligacion_core_ef BEFORE UPDATE ON public.composicion_obligacion FOR EACH ROW EXECUTE FUNCTION public.trg_core_ef_sync_defaults_update();


--
-- Name: concepto_financiero trg_bu_concepto_financiero_core_ef; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_bu_concepto_financiero_core_ef BEFORE UPDATE ON public.concepto_financiero FOR EACH ROW EXECUTE FUNCTION public.trg_core_ef_sync_defaults_update();


--
-- Name: desarrollo trg_bu_desarrollo_core_ef; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_bu_desarrollo_core_ef BEFORE UPDATE ON public.desarrollo FOR EACH ROW EXECUTE FUNCTION public.trg_core_ef_sync_defaults_update();


--
-- Name: desarrollo_sucursal trg_bu_desarrollo_sucursal_core_ef; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_bu_desarrollo_sucursal_core_ef BEFORE UPDATE ON public.desarrollo_sucursal FOR EACH ROW EXECUTE FUNCTION public.trg_core_ef_sync_defaults_update();


--
-- Name: disponibilidad trg_bu_disponibilidad_core_ef; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_bu_disponibilidad_core_ef BEFORE UPDATE ON public.disponibilidad FOR EACH ROW EXECUTE FUNCTION public.trg_core_ef_sync_defaults_update();


--
-- Name: documento_entidad trg_bu_documento_entidad_core_ef; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_bu_documento_entidad_core_ef BEFORE UPDATE ON public.documento_entidad FOR EACH ROW EXECUTE FUNCTION public.trg_core_ef_sync_defaults_update();


--
-- Name: emision_numeracion trg_bu_emision_numeracion_core_ef; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_bu_emision_numeracion_core_ef BEFORE UPDATE ON public.emision_numeracion FOR EACH ROW EXECUTE FUNCTION public.trg_core_ef_sync_defaults_update();


--
-- Name: factura_servicio trg_bu_factura_servicio_core_ef; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_bu_factura_servicio_core_ef BEFORE UPDATE ON public.factura_servicio FOR EACH ROW EXECUTE FUNCTION public.trg_core_ef_sync_defaults_update();


--
-- Name: inmueble trg_bu_inmueble_core_ef; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_bu_inmueble_core_ef BEFORE UPDATE ON public.inmueble FOR EACH ROW EXECUTE FUNCTION public.trg_core_ef_sync_defaults_update();


--
-- Name: inmueble_sucursal trg_bu_inmueble_sucursal_core_ef; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_bu_inmueble_sucursal_core_ef BEFORE UPDATE ON public.inmueble_sucursal FOR EACH ROW EXECUTE FUNCTION public.trg_core_ef_sync_defaults_update();


--
-- Name: instalacion trg_bu_instalacion_core_ef; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_bu_instalacion_core_ef BEFORE UPDATE ON public.instalacion FOR EACH ROW EXECUTE FUNCTION public.trg_core_ef_sync_defaults_update();


--
-- Name: movimiento_financiero trg_bu_movimiento_financiero_core_ef; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_bu_movimiento_financiero_core_ef BEFORE UPDATE ON public.movimiento_financiero FOR EACH ROW EXECUTE FUNCTION public.trg_core_ef_sync_defaults_update();


--
-- Name: obligacion_financiera trg_bu_obligacion_financiera_core_ef; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_bu_obligacion_financiera_core_ef BEFORE UPDATE ON public.obligacion_financiera FOR EACH ROW EXECUTE FUNCTION public.trg_core_ef_sync_defaults_update();


--
-- Name: ocupacion trg_bu_ocupacion_core_ef; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_bu_ocupacion_core_ef BEFORE UPDATE ON public.ocupacion FOR EACH ROW EXECUTE FUNCTION public.trg_core_ef_sync_defaults_update();


--
-- Name: persona_contacto trg_bu_persona_contacto_core_ef; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_bu_persona_contacto_core_ef BEFORE UPDATE ON public.persona_contacto FOR EACH ROW EXECUTE FUNCTION public.trg_core_ef_sync_defaults_update();


--
-- Name: persona trg_bu_persona_core_ef; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_bu_persona_core_ef BEFORE UPDATE ON public.persona FOR EACH ROW EXECUTE FUNCTION public.trg_core_ef_sync_defaults_update();


--
-- Name: persona_documento trg_bu_persona_documento_core_ef; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_bu_persona_documento_core_ef BEFORE UPDATE ON public.persona_documento FOR EACH ROW EXECUTE FUNCTION public.trg_core_ef_sync_defaults_update();


--
-- Name: persona_domicilio trg_bu_persona_domicilio_core_ef; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_bu_persona_domicilio_core_ef BEFORE UPDATE ON public.persona_domicilio FOR EACH ROW EXECUTE FUNCTION public.trg_core_ef_sync_defaults_update();


--
-- Name: persona_relacion trg_bu_persona_relacion_core_ef; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_bu_persona_relacion_core_ef BEFORE UPDATE ON public.persona_relacion FOR EACH ROW EXECUTE FUNCTION public.trg_core_ef_sync_defaults_update();


--
-- Name: relacion_generadora trg_bu_relacion_generadora_core_ef; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_bu_relacion_generadora_core_ef BEFORE UPDATE ON public.relacion_generadora FOR EACH ROW EXECUTE FUNCTION public.trg_core_ef_sync_defaults_update();


--
-- Name: relacion_persona_rol trg_bu_relacion_persona_rol_core_ef; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_bu_relacion_persona_rol_core_ef BEFORE UPDATE ON public.relacion_persona_rol FOR EACH ROW EXECUTE FUNCTION public.trg_core_ef_sync_defaults_update();


--
-- Name: representacion_poder trg_bu_representacion_poder_core_ef; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_bu_representacion_poder_core_ef BEFORE UPDATE ON public.representacion_poder FOR EACH ROW EXECUTE FUNCTION public.trg_core_ef_sync_defaults_update();


--
-- Name: rol_participacion trg_bu_rol_participacion_core_ef; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_bu_rol_participacion_core_ef BEFORE UPDATE ON public.rol_participacion FOR EACH ROW EXECUTE FUNCTION public.trg_core_ef_sync_defaults_update();


--
-- Name: sucursal trg_bu_sucursal_core_ef; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_bu_sucursal_core_ef BEFORE UPDATE ON public.sucursal FOR EACH ROW EXECUTE FUNCTION public.trg_core_ef_sync_defaults_update();


--
-- Name: unidad_funcional trg_bu_unidad_funcional_core_ef; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER trg_bu_unidad_funcional_core_ef BEFORE UPDATE ON public.unidad_funcional FOR EACH ROW EXECUTE FUNCTION public.trg_core_ef_sync_defaults_update();


--
-- Name: aplicacion_financiera fk_af_comp; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.aplicacion_financiera
    ADD CONSTRAINT fk_af_comp FOREIGN KEY (id_composicion_obligacion) REFERENCES public.composicion_obligacion(id_composicion_obligacion) ON DELETE RESTRICT;


--
-- Name: aplicacion_financiera fk_af_mov; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.aplicacion_financiera
    ADD CONSTRAINT fk_af_mov FOREIGN KEY (id_movimiento_financiero) REFERENCES public.movimiento_financiero(id_movimiento_financiero) ON DELETE RESTRICT;


--
-- Name: aplicacion_financiera fk_af_obl; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.aplicacion_financiera
    ADD CONSTRAINT fk_af_obl FOREIGN KEY (id_obligacion_financiera) REFERENCES public.obligacion_financiera(id_obligacion_financiera) ON DELETE RESTRICT;


--
-- Name: ajuste_alquiler fk_ajuste_contrato; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ajuste_alquiler
    ADD CONSTRAINT fk_ajuste_contrato FOREIGN KEY (id_contrato_alquiler) REFERENCES public.contrato_alquiler(id_contrato_alquiler) ON DELETE RESTRICT;


--
-- Name: alcance_autorizacion fk_alcance_rol; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alcance_autorizacion
    ADD CONSTRAINT fk_alcance_rol FOREIGN KEY (id_rol_seguridad) REFERENCES public.rol_seguridad(id_rol_seguridad) ON DELETE RESTRICT;


--
-- Name: archivo_digital fk_archivo_docv; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.archivo_digital
    ADD CONSTRAINT fk_archivo_docv FOREIGN KEY (id_documento_version) REFERENCES public.documento_version(id_documento_version) ON DELETE RESTRICT;


--
-- Name: evento_auditoria fk_aud_inst; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.evento_auditoria
    ADD CONSTRAINT fk_aud_inst FOREIGN KEY (id_instalacion) REFERENCES public.instalacion(id_instalacion) ON DELETE RESTRICT;


--
-- Name: evento_auditoria fk_aud_operacion; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.evento_auditoria
    ADD CONSTRAINT fk_aud_operacion FOREIGN KEY (id_operacion_auditoria) REFERENCES public.operacion_auditoria(id_operacion_auditoria) ON DELETE RESTRICT;


--
-- Name: evento_auditoria fk_aud_resultado; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.evento_auditoria
    ADD CONSTRAINT fk_aud_resultado FOREIGN KEY (id_resultado_evento_auditoria) REFERENCES public.resultado_evento_auditoria(id_resultado_evento_auditoria) ON DELETE RESTRICT;


--
-- Name: evento_auditoria fk_aud_sucursal; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.evento_auditoria
    ADD CONSTRAINT fk_aud_sucursal FOREIGN KEY (id_sucursal) REFERENCES public.sucursal(id_sucursal) ON DELETE RESTRICT;


--
-- Name: evento_auditoria fk_aud_tipo_evento; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.evento_auditoria
    ADD CONSTRAINT fk_aud_tipo_evento FOREIGN KEY (id_tipo_evento_auditoria) REFERENCES public.tipo_evento_auditoria(id_tipo_evento_auditoria) ON DELETE RESTRICT;


--
-- Name: evento_auditoria fk_aud_usuario; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.evento_auditoria
    ADD CONSTRAINT fk_aud_usuario FOREIGN KEY (id_usuario) REFERENCES public.usuario(id_usuario) ON DELETE RESTRICT;


--
-- Name: contrato_alquiler fk_ca_cartera; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contrato_alquiler
    ADD CONSTRAINT fk_ca_cartera FOREIGN KEY (id_cartera_locativa) REFERENCES public.cartera_locativa(id_cartera_locativa) ON DELETE RESTRICT;


--
-- Name: contrato_alquiler fk_ca_contrato_anterior; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contrato_alquiler
    ADD CONSTRAINT fk_ca_contrato_anterior FOREIGN KEY (id_contrato_anterior) REFERENCES public.contrato_alquiler(id_contrato_alquiler) ON DELETE RESTRICT;


--
-- Name: contrato_alquiler fk_ca_reserva; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contrato_alquiler
    ADD CONSTRAINT fk_ca_reserva FOREIGN KEY (id_reserva_locativa) REFERENCES public.reserva_locativa(id_reserva_locativa) ON DELETE RESTRICT;


--
-- Name: cartera_locativa fk_cartera_inmueble; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.cartera_locativa
    ADD CONSTRAINT fk_cartera_inmueble FOREIGN KEY (id_inmueble) REFERENCES public.inmueble(id_inmueble) ON DELETE RESTRICT;


--
-- Name: cartera_locativa fk_cartera_unidad; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.cartera_locativa
    ADD CONSTRAINT fk_cartera_unidad FOREIGN KEY (id_unidad_funcional) REFERENCES public.unidad_funcional(id_unidad_funcional) ON DELETE RESTRICT;


--
-- Name: conciliacion_bancaria fk_cb_cuenta; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.conciliacion_bancaria
    ADD CONSTRAINT fk_cb_cuenta FOREIGN KEY (id_cuenta_financiera) REFERENCES public.cuenta_financiera(id_cuenta_financiera) ON DELETE RESTRICT;


--
-- Name: condicion_economica_alquiler fk_cea_contrato; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.condicion_economica_alquiler
    ADD CONSTRAINT fk_cea_contrato FOREIGN KEY (id_contrato_alquiler) REFERENCES public.contrato_alquiler(id_contrato_alquiler) ON DELETE RESTRICT;


--
-- Name: cesion fk_cesion_venta; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.cesion
    ADD CONSTRAINT fk_cesion_venta FOREIGN KEY (id_venta) REFERENCES public.venta(id_venta) ON DELETE RESTRICT;


--
-- Name: cliente_comprador fk_cliente_persona; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.cliente_comprador
    ADD CONSTRAINT fk_cliente_persona FOREIGN KEY (id_persona) REFERENCES public.persona(id_persona) ON DELETE RESTRICT;


--
-- Name: composicion_obligacion fk_co_concepto; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.composicion_obligacion
    ADD CONSTRAINT fk_co_concepto FOREIGN KEY (id_concepto_financiero) REFERENCES public.concepto_financiero(id_concepto_financiero) ON DELETE RESTRICT;


--
-- Name: composicion_obligacion fk_co_obl; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.composicion_obligacion
    ADD CONSTRAINT fk_co_obl FOREIGN KEY (id_obligacion_financiera) REFERENCES public.obligacion_financiera(id_obligacion_financiera) ON DELETE RESTRICT;


--
-- Name: contrato_objeto_locativo fk_col_contrato; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contrato_objeto_locativo
    ADD CONSTRAINT fk_col_contrato FOREIGN KEY (id_contrato_alquiler) REFERENCES public.contrato_alquiler(id_contrato_alquiler) ON DELETE RESTRICT;


--
-- Name: contrato_objeto_locativo fk_col_inmueble; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contrato_objeto_locativo
    ADD CONSTRAINT fk_col_inmueble FOREIGN KEY (id_inmueble) REFERENCES public.inmueble(id_inmueble) ON DELETE RESTRICT;


--
-- Name: contrato_objeto_locativo fk_col_unidad; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contrato_objeto_locativo
    ADD CONSTRAINT fk_col_unidad FOREIGN KEY (id_unidad_funcional) REFERENCES public.unidad_funcional(id_unidad_funcional) ON DELETE RESTRICT;


--
-- Name: credencial_usuario fk_cred_usuario; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.credencial_usuario
    ADD CONSTRAINT fk_cred_usuario FOREIGN KEY (id_usuario) REFERENCES public.usuario(id_usuario) ON DELETE RESTRICT;


--
-- Name: cuenta_financiera fk_cuenta_financiera_sucursal; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.cuenta_financiera
    ADD CONSTRAINT fk_cuenta_financiera_sucursal FOREIGN KEY (id_sucursal_operativa) REFERENCES public.sucursal(id_sucursal) ON DELETE RESTRICT;


--
-- Name: detalle_conciliacion fk_dc_cb; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.detalle_conciliacion
    ADD CONSTRAINT fk_dc_cb FOREIGN KEY (id_conciliacion_bancaria) REFERENCES public.conciliacion_bancaria(id_conciliacion_bancaria) ON DELETE RESTRICT;


--
-- Name: detalle_conciliacion fk_dc_mt; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.detalle_conciliacion
    ADD CONSTRAINT fk_dc_mt FOREIGN KEY (id_movimiento_tesoreria) REFERENCES public.movimiento_tesoreria(id_movimiento_tesoreria) ON DELETE RESTRICT;


--
-- Name: documento_entidad fk_de_doc; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documento_entidad
    ADD CONSTRAINT fk_de_doc FOREIGN KEY (id_documento_logico) REFERENCES public.documento_logico(id_documento_logico) ON DELETE RESTRICT;


--
-- Name: denegacion_explicita fk_den_permiso; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.denegacion_explicita
    ADD CONSTRAINT fk_den_permiso FOREIGN KEY (id_permiso) REFERENCES public.permiso(id_permiso) ON DELETE RESTRICT;


--
-- Name: denegacion_explicita fk_den_usuario; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.denegacion_explicita
    ADD CONSTRAINT fk_den_usuario FOREIGN KEY (id_usuario) REFERENCES public.usuario(id_usuario) ON DELETE RESTRICT;


--
-- Name: desarrollo_sucursal fk_desarrollo_sucursal_desarrollo; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.desarrollo_sucursal
    ADD CONSTRAINT fk_desarrollo_sucursal_desarrollo FOREIGN KEY (id_desarrollo) REFERENCES public.desarrollo(id_desarrollo) ON DELETE RESTRICT;


--
-- Name: desarrollo_sucursal fk_desarrollo_sucursal_sucursal; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.desarrollo_sucursal
    ADD CONSTRAINT fk_desarrollo_sucursal_sucursal FOREIGN KEY (id_sucursal) REFERENCES public.sucursal(id_sucursal) ON DELETE RESTRICT;


--
-- Name: detalle_cambio_auditoria fk_det_cambio_evento; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.detalle_cambio_auditoria
    ADD CONSTRAINT fk_det_cambio_evento FOREIGN KEY (id_evento_auditoria) REFERENCES public.evento_auditoria(id_evento_auditoria) ON DELETE RESTRICT;


--
-- Name: disponibilidad fk_disp_inmueble; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.disponibilidad
    ADD CONSTRAINT fk_disp_inmueble FOREIGN KEY (id_inmueble) REFERENCES public.inmueble(id_inmueble) ON DELETE RESTRICT;


--
-- Name: disponibilidad fk_disp_unidad; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.disponibilidad
    ADD CONSTRAINT fk_disp_unidad FOREIGN KEY (id_unidad_funcional) REFERENCES public.unidad_funcional(id_unidad_funcional) ON DELETE RESTRICT;


--
-- Name: documento_logico fk_doc_inst_creadora; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documento_logico
    ADD CONSTRAINT fk_doc_inst_creadora FOREIGN KEY (id_instalacion_creadora) REFERENCES public.instalacion(id_instalacion) ON DELETE RESTRICT;


--
-- Name: documento_logico fk_doc_sucursal_origen; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documento_logico
    ADD CONSTRAINT fk_doc_sucursal_origen FOREIGN KEY (id_sucursal_origen) REFERENCES public.sucursal(id_sucursal) ON DELETE RESTRICT;


--
-- Name: documento_logico fk_doc_tipo; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documento_logico
    ADD CONSTRAINT fk_doc_tipo FOREIGN KEY (id_tipo_documental) REFERENCES public.tipo_documental(id_tipo_documental) ON DELETE RESTRICT;


--
-- Name: documento_version fk_docv_doc; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documento_version
    ADD CONSTRAINT fk_docv_doc FOREIGN KEY (id_documento_logico) REFERENCES public.documento_logico(id_documento_logico) ON DELETE RESTRICT;


--
-- Name: edificacion fk_edif_inmueble; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.edificacion
    ADD CONSTRAINT fk_edif_inmueble FOREIGN KEY (id_inmueble) REFERENCES public.inmueble(id_inmueble) ON DELETE RESTRICT;


--
-- Name: edificacion fk_edif_unidad; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.edificacion
    ADD CONSTRAINT fk_edif_unidad FOREIGN KEY (id_unidad_funcional) REFERENCES public.unidad_funcional(id_unidad_funcional) ON DELETE RESTRICT;


--
-- Name: emision_numeracion fk_en_serie; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.emision_numeracion
    ADD CONSTRAINT fk_en_serie FOREIGN KEY (id_numerador_serie) REFERENCES public.numerador_serie(id_numerador_serie) ON DELETE RESTRICT;


--
-- Name: entrega_restitucion_inmueble fk_entrega_contrato; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.entrega_restitucion_inmueble
    ADD CONSTRAINT fk_entrega_contrato FOREIGN KEY (id_contrato_alquiler) REFERENCES public.contrato_alquiler(id_contrato_alquiler) ON DELETE RESTRICT;


--
-- Name: escrituracion fk_escritura_venta; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.escrituracion
    ADD CONSTRAINT fk_escritura_venta FOREIGN KEY (id_venta) REFERENCES public.venta(id_venta) ON DELETE RESTRICT;


--
-- Name: evento_numeracion fk_ev_num; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.evento_numeracion
    ADD CONSTRAINT fk_ev_num FOREIGN KEY (id_emision_numeracion) REFERENCES public.emision_numeracion(id_emision_numeracion) ON DELETE RESTRICT;


--
-- Name: factura_servicio fk_factura_servicio_inmueble; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.factura_servicio
    ADD CONSTRAINT fk_factura_servicio_inmueble FOREIGN KEY (id_inmueble) REFERENCES public.inmueble(id_inmueble) ON DELETE RESTRICT;


--
-- Name: factura_servicio fk_factura_servicio_servicio; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.factura_servicio
    ADD CONSTRAINT fk_factura_servicio_servicio FOREIGN KEY (id_servicio) REFERENCES public.servicio(id_servicio) ON DELETE RESTRICT;


--
-- Name: factura_servicio fk_factura_servicio_unidad_funcional; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.factura_servicio
    ADD CONSTRAINT fk_factura_servicio_unidad_funcional FOREIGN KEY (id_unidad_funcional) REFERENCES public.unidad_funcional(id_unidad_funcional) ON DELETE RESTRICT;


--
-- Name: historial_acceso fk_ha_credencial; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.historial_acceso
    ADD CONSTRAINT fk_ha_credencial FOREIGN KEY (id_credencial_usuario) REFERENCES public.credencial_usuario(id_credencial_usuario) ON DELETE RESTRICT;


--
-- Name: historial_acceso fk_ha_inst; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.historial_acceso
    ADD CONSTRAINT fk_ha_inst FOREIGN KEY (id_instalacion_contexto) REFERENCES public.instalacion(id_instalacion) ON DELETE RESTRICT;


--
-- Name: historial_acceso fk_ha_sesion; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.historial_acceso
    ADD CONSTRAINT fk_ha_sesion FOREIGN KEY (id_sesion_usuario) REFERENCES public.sesion_usuario(id_sesion_usuario) ON DELETE RESTRICT;


--
-- Name: historial_acceso fk_ha_sucursal; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.historial_acceso
    ADD CONSTRAINT fk_ha_sucursal FOREIGN KEY (id_sucursal_contexto) REFERENCES public.sucursal(id_sucursal) ON DELETE RESTRICT;


--
-- Name: historial_acceso fk_ha_usuario; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.historial_acceso
    ADD CONSTRAINT fk_ha_usuario FOREIGN KEY (id_usuario) REFERENCES public.usuario(id_usuario) ON DELETE RESTRICT;


--
-- Name: historial_catalogo fk_historial_catalogo; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.historial_catalogo
    ADD CONSTRAINT fk_historial_catalogo FOREIGN KEY (id_catalogo_maestro) REFERENCES public.catalogo_maestro(id_catalogo_maestro) ON DELETE RESTRICT;


--
-- Name: historial_parametro fk_historial_parametro; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.historial_parametro
    ADD CONSTRAINT fk_historial_parametro FOREIGN KEY (id_parametro_sistema) REFERENCES public.parametro_sistema(id_parametro_sistema) ON DELETE RESTRICT;


--
-- Name: instrumento_compraventa fk_ic_venta; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.instrumento_compraventa
    ADD CONSTRAINT fk_ic_venta FOREIGN KEY (id_venta) REFERENCES public.venta(id_venta) ON DELETE RESTRICT;


--
-- Name: inmueble fk_inmueble_desarrollo; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.inmueble
    ADD CONSTRAINT fk_inmueble_desarrollo FOREIGN KEY (id_desarrollo) REFERENCES public.desarrollo(id_desarrollo) ON DELETE RESTRICT;


--
-- Name: inmueble_sucursal fk_inmueble_sucursal_inmueble; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.inmueble_sucursal
    ADD CONSTRAINT fk_inmueble_sucursal_inmueble FOREIGN KEY (id_inmueble) REFERENCES public.inmueble(id_inmueble) ON DELETE RESTRICT;


--
-- Name: inmueble_sucursal fk_inmueble_sucursal_sucursal; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.inmueble_sucursal
    ADD CONSTRAINT fk_inmueble_sucursal_sucursal FOREIGN KEY (id_sucursal) REFERENCES public.sucursal(id_sucursal) ON DELETE RESTRICT;


--
-- Name: instalacion fk_instalacion_sucursal; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.instalacion
    ADD CONSTRAINT fk_instalacion_sucursal FOREIGN KEY (id_sucursal) REFERENCES public.sucursal(id_sucursal) ON DELETE RESTRICT;


--
-- Name: instrumento_objeto_inmobiliario fk_io_inmueble; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.instrumento_objeto_inmobiliario
    ADD CONSTRAINT fk_io_inmueble FOREIGN KEY (id_inmueble) REFERENCES public.inmueble(id_inmueble) ON DELETE RESTRICT;


--
-- Name: instrumento_objeto_inmobiliario fk_io_instrumento; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.instrumento_objeto_inmobiliario
    ADD CONSTRAINT fk_io_instrumento FOREIGN KEY (id_instrumento_compraventa) REFERENCES public.instrumento_compraventa(id_instrumento_compraventa) ON DELETE RESTRICT;


--
-- Name: instrumento_objeto_inmobiliario fk_io_unidad; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.instrumento_objeto_inmobiliario
    ADD CONSTRAINT fk_io_unidad FOREIGN KEY (id_unidad_funcional) REFERENCES public.unidad_funcional(id_unidad_funcional) ON DELETE RESTRICT;


--
-- Name: item_catalogo fk_item_catalogo_catalogo; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.item_catalogo
    ADD CONSTRAINT fk_item_catalogo_catalogo FOREIGN KEY (id_catalogo_maestro) REFERENCES public.catalogo_maestro(id_catalogo_maestro) ON DELETE RESTRICT;


--
-- Name: jerarquia_item_catalogo fk_jerarquia_item_hijo; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.jerarquia_item_catalogo
    ADD CONSTRAINT fk_jerarquia_item_hijo FOREIGN KEY (id_item_catalogo_hijo) REFERENCES public.item_catalogo(id_item_catalogo) ON DELETE RESTRICT;


--
-- Name: jerarquia_item_catalogo fk_jerarquia_item_padre; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.jerarquia_item_catalogo
    ADD CONSTRAINT fk_jerarquia_item_padre FOREIGN KEY (id_item_catalogo_padre) REFERENCES public.item_catalogo(id_item_catalogo) ON DELETE RESTRICT;


--
-- Name: lock_logico fk_lock_instalacion; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lock_logico
    ADD CONSTRAINT fk_lock_instalacion FOREIGN KEY (id_instalacion_origen) REFERENCES public.instalacion(id_instalacion) ON DELETE RESTRICT;


--
-- Name: modificacion_locativa fk_mod_contrato; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.modificacion_locativa
    ADD CONSTRAINT fk_mod_contrato FOREIGN KEY (id_contrato_alquiler) REFERENCES public.contrato_alquiler(id_contrato_alquiler) ON DELETE RESTRICT;


--
-- Name: movimiento_tesoreria fk_mt_cuenta_destino; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.movimiento_tesoreria
    ADD CONSTRAINT fk_mt_cuenta_destino FOREIGN KEY (id_cuenta_financiera_destino) REFERENCES public.cuenta_financiera(id_cuenta_financiera) ON DELETE RESTRICT;


--
-- Name: movimiento_tesoreria fk_mt_cuenta_origen; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.movimiento_tesoreria
    ADD CONSTRAINT fk_mt_cuenta_origen FOREIGN KEY (id_cuenta_financiera_origen) REFERENCES public.cuenta_financiera(id_cuenta_financiera) ON DELETE RESTRICT;


--
-- Name: movimiento_tesoreria fk_mt_mov_fin; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.movimiento_tesoreria
    ADD CONSTRAINT fk_mt_mov_fin FOREIGN KEY (id_movimiento_financiero) REFERENCES public.movimiento_financiero(id_movimiento_financiero) ON DELETE RESTRICT;


--
-- Name: movimiento_tesoreria fk_mt_sucursal; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.movimiento_tesoreria
    ADD CONSTRAINT fk_mt_sucursal FOREIGN KEY (id_sucursal_operativa) REFERENCES public.sucursal(id_sucursal) ON DELETE RESTRICT;


--
-- Name: numerador_serie fk_ns_numerador; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.numerador_serie
    ADD CONSTRAINT fk_ns_numerador FOREIGN KEY (id_numerador_documental) REFERENCES public.numerador_documental(id_numerador_documental) ON DELETE RESTRICT;


--
-- Name: numerador_serie fk_ns_sucursal; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.numerador_serie
    ADD CONSTRAINT fk_ns_sucursal FOREIGN KEY (id_sucursal) REFERENCES public.sucursal(id_sucursal) ON DELETE RESTRICT;


--
-- Name: obligacion_financiera fk_obl_rg; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.obligacion_financiera
    ADD CONSTRAINT fk_obl_rg FOREIGN KEY (id_relacion_generadora) REFERENCES public.relacion_generadora(id_relacion_generadora) ON DELETE RESTRICT;


--
-- Name: obligacion_financiera fk_obl_reemplazada; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.obligacion_financiera
    ADD CONSTRAINT fk_obl_reemplazada FOREIGN KEY (id_obligacion_reemplazada) REFERENCES public.obligacion_financiera(id_obligacion_financiera) ON DELETE RESTRICT;


--
-- Name: obligacion_financiera fk_obl_reemplazante; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.obligacion_financiera
    ADD CONSTRAINT fk_obl_reemplazante FOREIGN KEY (id_obligacion_reemplazante) REFERENCES public.obligacion_financiera(id_obligacion_financiera) ON DELETE RESTRICT;


--
-- Name: ocupacion fk_oc_inmueble; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ocupacion
    ADD CONSTRAINT fk_oc_inmueble FOREIGN KEY (id_inmueble) REFERENCES public.inmueble(id_inmueble) ON DELETE RESTRICT;


--
-- Name: ocupacion fk_oc_unidad; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.ocupacion
    ADD CONSTRAINT fk_oc_unidad FOREIGN KEY (id_unidad_funcional) REFERENCES public.unidad_funcional(id_unidad_funcional) ON DELETE RESTRICT;


--
-- Name: obligacion_obligado fk_oo_obl; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.obligacion_obligado
    ADD CONSTRAINT fk_oo_obl FOREIGN KEY (id_obligacion_financiera) REFERENCES public.obligacion_financiera(id_obligacion_financiera) ON DELETE RESTRICT;


--
-- Name: obligacion_obligado fk_oo_persona; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.obligacion_obligado
    ADD CONSTRAINT fk_oo_persona FOREIGN KEY (id_persona) REFERENCES public.persona(id_persona) ON DELETE RESTRICT;


--
-- Name: parametro_sistema fk_parametro_alcance; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.parametro_sistema
    ADD CONSTRAINT fk_parametro_alcance FOREIGN KEY (id_alcance_parametro) REFERENCES public.alcance_parametro(id_alcance_parametro) ON DELETE RESTRICT;


--
-- Name: parametro_opcion fk_parametro_opcion_parametro; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.parametro_opcion
    ADD CONSTRAINT fk_parametro_opcion_parametro FOREIGN KEY (id_parametro_sistema) REFERENCES public.parametro_sistema(id_parametro_sistema) ON DELETE RESTRICT;


--
-- Name: parametro_sistema fk_parametro_tipo_dato; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.parametro_sistema
    ADD CONSTRAINT fk_parametro_tipo_dato FOREIGN KEY (id_tipo_dato_parametro) REFERENCES public.tipo_dato_parametro(id_tipo_dato_parametro) ON DELETE RESTRICT;


--
-- Name: persona_contacto fk_pcont_persona; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.persona_contacto
    ADD CONSTRAINT fk_pcont_persona FOREIGN KEY (id_persona) REFERENCES public.persona(id_persona) ON DELETE RESTRICT;


--
-- Name: persona_documento fk_pd_persona; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.persona_documento
    ADD CONSTRAINT fk_pd_persona FOREIGN KEY (id_persona) REFERENCES public.persona(id_persona) ON DELETE RESTRICT;


--
-- Name: persona_domicilio fk_pdom_persona; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.persona_domicilio
    ADD CONSTRAINT fk_pdom_persona FOREIGN KEY (id_persona) REFERENCES public.persona(id_persona) ON DELETE RESTRICT;


--
-- Name: persona_relacion fk_pr_destino; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.persona_relacion
    ADD CONSTRAINT fk_pr_destino FOREIGN KEY (id_persona_destino) REFERENCES public.persona(id_persona) ON DELETE RESTRICT;


--
-- Name: persona_relacion fk_pr_origen; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.persona_relacion
    ADD CONSTRAINT fk_pr_origen FOREIGN KEY (id_persona_origen) REFERENCES public.persona(id_persona) ON DELETE RESTRICT;


--
-- Name: representacion_poder fk_rep_representado; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.representacion_poder
    ADD CONSTRAINT fk_rep_representado FOREIGN KEY (id_persona_representado) REFERENCES public.persona(id_persona) ON DELETE RESTRICT;


--
-- Name: representacion_poder fk_rep_representante; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.representacion_poder
    ADD CONSTRAINT fk_rep_representante FOREIGN KEY (id_persona_representante) REFERENCES public.persona(id_persona) ON DELETE RESTRICT;


--
-- Name: rescision_finalizacion_alquiler fk_resc_loc_contrato; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rescision_finalizacion_alquiler
    ADD CONSTRAINT fk_resc_loc_contrato FOREIGN KEY (id_contrato_alquiler) REFERENCES public.contrato_alquiler(id_contrato_alquiler) ON DELETE RESTRICT;


--
-- Name: rescision_venta fk_rescision_venta; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rescision_venta
    ADD CONSTRAINT fk_rescision_venta FOREIGN KEY (id_venta) REFERENCES public.venta(id_venta) ON DELETE RESTRICT;


--
-- Name: reserva_locativa fk_rl_solicitud; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.reserva_locativa
    ADD CONSTRAINT fk_rl_solicitud FOREIGN KEY (id_solicitud_alquiler) REFERENCES public.solicitud_alquiler(id_solicitud_alquiler) ON DELETE RESTRICT;


--
-- Name: relacion_persona_rol fk_rpr_persona; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.relacion_persona_rol
    ADD CONSTRAINT fk_rpr_persona FOREIGN KEY (id_persona) REFERENCES public.persona(id_persona) ON DELETE RESTRICT;


--
-- Name: relacion_persona_rol fk_rpr_rol; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.relacion_persona_rol
    ADD CONSTRAINT fk_rpr_rol FOREIGN KEY (id_rol_participacion) REFERENCES public.rol_participacion(id_rol_participacion) ON DELETE RESTRICT;


--
-- Name: rol_seguridad_permiso fk_rsp_permiso; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rol_seguridad_permiso
    ADD CONSTRAINT fk_rsp_permiso FOREIGN KEY (id_permiso) REFERENCES public.permiso(id_permiso) ON DELETE RESTRICT;


--
-- Name: rol_seguridad_permiso fk_rsp_rol; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rol_seguridad_permiso
    ADD CONSTRAINT fk_rsp_rol FOREIGN KEY (id_rol_seguridad) REFERENCES public.rol_seguridad(id_rol_seguridad) ON DELETE RESTRICT;


--
-- Name: sesion_usuario fk_sesion_credencial; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sesion_usuario
    ADD CONSTRAINT fk_sesion_credencial FOREIGN KEY (id_credencial_usuario) REFERENCES public.credencial_usuario(id_credencial_usuario) ON DELETE RESTRICT;


--
-- Name: sesion_usuario fk_sesion_inst; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sesion_usuario
    ADD CONSTRAINT fk_sesion_inst FOREIGN KEY (id_instalacion_origen) REFERENCES public.instalacion(id_instalacion) ON DELETE RESTRICT;


--
-- Name: sesion_usuario fk_sesion_sucursal; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sesion_usuario
    ADD CONSTRAINT fk_sesion_sucursal FOREIGN KEY (id_sucursal_operativa) REFERENCES public.sucursal(id_sucursal) ON DELETE RESTRICT;


--
-- Name: sesion_usuario fk_sesion_usuario; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sesion_usuario
    ADD CONSTRAINT fk_sesion_usuario FOREIGN KEY (id_usuario) REFERENCES public.usuario(id_usuario) ON DELETE RESTRICT;


--
-- Name: sincronizacion_operacion fk_sinc_operacion_paquete; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sincronizacion_operacion
    ADD CONSTRAINT fk_sinc_operacion_paquete FOREIGN KEY (id_sincronizacion_paquete) REFERENCES public.sincronizacion_paquete(id_sincronizacion_paquete) ON DELETE RESTRICT;


--
-- Name: sincronizacion_paquete fk_sinc_paquete_inst_origen; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sincronizacion_paquete
    ADD CONSTRAINT fk_sinc_paquete_inst_origen FOREIGN KEY (id_instalacion_origen) REFERENCES public.instalacion(id_instalacion) ON DELETE RESTRICT;


--
-- Name: sincronizacion_recepcion fk_sinc_recepcion_conflicto; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sincronizacion_recepcion
    ADD CONSTRAINT fk_sinc_recepcion_conflicto FOREIGN KEY (id_conflicto_sincronizacion) REFERENCES public.conflicto_sincronizacion(id_conflicto_sincronizacion) ON DELETE RESTRICT;


--
-- Name: sincronizacion_recepcion fk_sinc_recepcion_inst_origen; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sincronizacion_recepcion
    ADD CONSTRAINT fk_sinc_recepcion_inst_origen FOREIGN KEY (id_instalacion_origen) REFERENCES public.instalacion(id_instalacion) ON DELETE RESTRICT;


--
-- Name: sincronizacion_recepcion fk_sinc_recepcion_inst_receptora; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sincronizacion_recepcion
    ADD CONSTRAINT fk_sinc_recepcion_inst_receptora FOREIGN KEY (id_instalacion_receptora) REFERENCES public.instalacion(id_instalacion) ON DELETE RESTRICT;


--
-- Name: inmueble_servicio fk_ts_inmueble; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.inmueble_servicio
    ADD CONSTRAINT fk_ts_inmueble FOREIGN KEY (id_inmueble) REFERENCES public.inmueble(id_inmueble) ON DELETE RESTRICT;


--
-- Name: inmueble_servicio fk_ts_servicio; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.inmueble_servicio
    ADD CONSTRAINT fk_ts_servicio FOREIGN KEY (id_servicio) REFERENCES public.servicio(id_servicio) ON DELETE RESTRICT;


--
-- Name: unidad_funcional_servicio fk_ufs_servicio; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.unidad_funcional_servicio
    ADD CONSTRAINT fk_ufs_servicio FOREIGN KEY (id_servicio) REFERENCES public.servicio(id_servicio) ON DELETE RESTRICT;


--
-- Name: unidad_funcional_servicio fk_ufs_unidad; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.unidad_funcional_servicio
    ADD CONSTRAINT fk_ufs_unidad FOREIGN KEY (id_unidad_funcional) REFERENCES public.unidad_funcional(id_unidad_funcional) ON DELETE RESTRICT;


--
-- Name: unidad_funcional fk_unidad_inmueble; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.unidad_funcional
    ADD CONSTRAINT fk_unidad_inmueble FOREIGN KEY (id_inmueble) REFERENCES public.inmueble(id_inmueble) ON DELETE RESTRICT;


--
-- Name: usuario_persona fk_up_persona; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usuario_persona
    ADD CONSTRAINT fk_up_persona FOREIGN KEY (id_persona) REFERENCES public.persona(id_persona) ON DELETE RESTRICT;


--
-- Name: usuario_persona fk_up_usuario; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usuario_persona
    ADD CONSTRAINT fk_up_usuario FOREIGN KEY (id_usuario) REFERENCES public.usuario(id_usuario) ON DELETE RESTRICT;


--
-- Name: usuario_rol_seguridad fk_urs_rol; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usuario_rol_seguridad
    ADD CONSTRAINT fk_urs_rol FOREIGN KEY (id_rol_seguridad) REFERENCES public.rol_seguridad(id_rol_seguridad) ON DELETE RESTRICT;


--
-- Name: usuario_rol_seguridad fk_urs_usuario; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usuario_rol_seguridad
    ADD CONSTRAINT fk_urs_usuario FOREIGN KEY (id_usuario) REFERENCES public.usuario(id_usuario) ON DELETE RESTRICT;


--
-- Name: usuario_rol_sucursal fk_ursc_rol; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usuario_rol_sucursal
    ADD CONSTRAINT fk_ursc_rol FOREIGN KEY (id_rol_seguridad) REFERENCES public.rol_seguridad(id_rol_seguridad) ON DELETE RESTRICT;


--
-- Name: usuario_rol_sucursal fk_ursc_sucursal; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usuario_rol_sucursal
    ADD CONSTRAINT fk_ursc_sucursal FOREIGN KEY (id_sucursal) REFERENCES public.sucursal(id_sucursal) ON DELETE RESTRICT;


--
-- Name: usuario_rol_sucursal fk_ursc_usuario; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usuario_rol_sucursal
    ADD CONSTRAINT fk_ursc_usuario FOREIGN KEY (id_usuario) REFERENCES public.usuario(id_usuario) ON DELETE RESTRICT;


--
-- Name: usuario_sucursal fk_us_sucursal; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usuario_sucursal
    ADD CONSTRAINT fk_us_sucursal FOREIGN KEY (id_sucursal) REFERENCES public.sucursal(id_sucursal) ON DELETE RESTRICT;


--
-- Name: usuario_sucursal fk_us_usuario; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.usuario_sucursal
    ADD CONSTRAINT fk_us_usuario FOREIGN KEY (id_usuario) REFERENCES public.usuario(id_usuario) ON DELETE RESTRICT;


--
-- Name: valor_parametro fk_valor_parametro_instalacion; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.valor_parametro
    ADD CONSTRAINT fk_valor_parametro_instalacion FOREIGN KEY (id_instalacion) REFERENCES public.instalacion(id_instalacion) ON DELETE RESTRICT;


--
-- Name: valor_parametro fk_valor_parametro_parametro; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.valor_parametro
    ADD CONSTRAINT fk_valor_parametro_parametro FOREIGN KEY (id_parametro_sistema) REFERENCES public.parametro_sistema(id_parametro_sistema) ON DELETE RESTRICT;


--
-- Name: valor_parametro fk_valor_parametro_sucursal; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.valor_parametro
    ADD CONSTRAINT fk_valor_parametro_sucursal FOREIGN KEY (id_sucursal) REFERENCES public.sucursal(id_sucursal) ON DELETE RESTRICT;


--
-- Name: venta fk_venta_reserva; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.venta
    ADD CONSTRAINT fk_venta_reserva FOREIGN KEY (id_reserva_venta) REFERENCES public.reserva_venta(id_reserva_venta) ON DELETE RESTRICT;


--
-- Name: venta_objeto_inmobiliario fk_vo_inmueble; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.venta_objeto_inmobiliario
    ADD CONSTRAINT fk_vo_inmueble FOREIGN KEY (id_inmueble) REFERENCES public.inmueble(id_inmueble) ON DELETE RESTRICT;


--
-- Name: venta_objeto_inmobiliario fk_vo_unidad; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.venta_objeto_inmobiliario
    ADD CONSTRAINT fk_vo_unidad FOREIGN KEY (id_unidad_funcional) REFERENCES public.unidad_funcional(id_unidad_funcional) ON DELETE RESTRICT;


--
-- Name: venta_objeto_inmobiliario fk_vo_venta; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.venta_objeto_inmobiliario
    ADD CONSTRAINT fk_vo_venta FOREIGN KEY (id_venta) REFERENCES public.venta(id_venta) ON DELETE RESTRICT;


--
-- Name: reserva_venta_objeto_inmobiliario; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.reserva_venta_objeto_inmobiliario (
    id_reserva_venta_objeto bigint NOT NULL,
    uid_global uuid DEFAULT gen_random_uuid() NOT NULL,
    version_registro integer DEFAULT 1 NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    deleted_at timestamp without time zone,
    id_instalacion_origen bigint,
    id_instalacion_ultima_modificacion bigint,
    op_id_alta uuid,
    op_id_ultima_modificacion uuid,
    id_reserva_venta bigint NOT NULL,
    id_inmueble bigint,
    id_unidad_funcional bigint,
    observaciones text,
    CONSTRAINT chk_rvo_xor CHECK ((((id_inmueble IS NOT NULL) AND (id_unidad_funcional IS NULL)) OR ((id_inmueble IS NULL) AND (id_unidad_funcional IS NOT NULL))))
);


--
-- Name: reserva_venta_objeto_inmobiliario_id_reserva_venta_objeto_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.reserva_venta_objeto_inmobiliario_id_reserva_venta_objeto_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: reserva_venta_objeto_inmobiliario_id_reserva_venta_objeto_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.reserva_venta_objeto_inmobiliario_id_reserva_venta_objeto_seq OWNED BY public.reserva_venta_objeto_inmobiliario.id_reserva_venta_objeto;


--
-- Name: reserva_venta_objeto_inmobiliario id_reserva_venta_objeto; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.reserva_venta_objeto_inmobiliario ALTER COLUMN id_reserva_venta_objeto SET DEFAULT nextval('public.reserva_venta_objeto_inmobiliario_id_reserva_venta_objeto_seq'::regclass);


--
-- Name: reserva_venta_objeto_inmobiliario reserva_venta_objeto_inmobiliario_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.reserva_venta_objeto_inmobiliario
    ADD CONSTRAINT reserva_venta_objeto_inmobiliario_pkey PRIMARY KEY (id_reserva_venta_objeto);


--
-- Name: reserva_venta_objeto_inmobiliario uq_reserva_venta_objeto_uid_global; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.reserva_venta_objeto_inmobiliario
    ADD CONSTRAINT uq_reserva_venta_objeto_uid_global UNIQUE (uid_global);


--
-- Name: idx_reserva_venta_objeto_uid_global; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_reserva_venta_objeto_uid_global ON public.reserva_venta_objeto_inmobiliario USING btree (uid_global);


--
-- Name: idx_rvo_inmueble; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_rvo_inmueble ON public.reserva_venta_objeto_inmobiliario USING btree (id_inmueble);


--
-- Name: idx_rvo_reserva; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_rvo_reserva ON public.reserva_venta_objeto_inmobiliario USING btree (id_reserva_venta);


--
-- Name: idx_rvo_unidad; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_rvo_unidad ON public.reserva_venta_objeto_inmobiliario USING btree (id_unidad_funcional);


--
-- Name: uq_rvo_reserva_inmueble_activo; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_rvo_reserva_inmueble_activo ON public.reserva_venta_objeto_inmobiliario USING btree (id_reserva_venta, id_inmueble) WHERE ((deleted_at IS NULL) AND (id_inmueble IS NOT NULL));


--
-- Name: uq_rvo_reserva_unidad_activo; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_rvo_reserva_unidad_activo ON public.reserva_venta_objeto_inmobiliario USING btree (id_reserva_venta, id_unidad_funcional) WHERE ((deleted_at IS NULL) AND (id_unidad_funcional IS NOT NULL));


--
-- Name: reserva_venta_objeto_inmobiliario fk_rvo_inmueble; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.reserva_venta_objeto_inmobiliario
    ADD CONSTRAINT fk_rvo_inmueble FOREIGN KEY (id_inmueble) REFERENCES public.inmueble(id_inmueble) ON DELETE RESTRICT;


--
-- Name: reserva_venta_objeto_inmobiliario fk_rvo_reserva; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.reserva_venta_objeto_inmobiliario
    ADD CONSTRAINT fk_rvo_reserva FOREIGN KEY (id_reserva_venta) REFERENCES public.reserva_venta(id_reserva_venta) ON DELETE RESTRICT;


--
-- Name: reserva_venta_objeto_inmobiliario fk_rvo_unidad; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.reserva_venta_objeto_inmobiliario
    ADD CONSTRAINT fk_rvo_unidad FOREIGN KEY (id_unidad_funcional) REFERENCES public.unidad_funcional(id_unidad_funcional) ON DELETE RESTRICT;


--
-- Name: reserva_locativa_objeto; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.reserva_locativa_objeto (
    id_reserva_locativa_objeto bigint NOT NULL,
    uid_global uuid DEFAULT gen_random_uuid() NOT NULL,
    version_registro integer DEFAULT 1 NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    deleted_at timestamp without time zone,
    id_instalacion_origen bigint,
    id_instalacion_ultima_modificacion bigint,
    op_id_alta uuid,
    op_id_ultima_modificacion uuid,
    id_reserva_locativa bigint NOT NULL,
    id_inmueble bigint,
    id_unidad_funcional bigint,
    observaciones text,
    CONSTRAINT chk_rlo_xor CHECK ((((id_inmueble IS NOT NULL) AND (id_unidad_funcional IS NULL)) OR ((id_inmueble IS NULL) AND (id_unidad_funcional IS NOT NULL))))
);


--
-- Name: reserva_locativa_objeto_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.reserva_locativa_objeto_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: reserva_locativa_objeto_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.reserva_locativa_objeto_id_seq OWNED BY public.reserva_locativa_objeto.id_reserva_locativa_objeto;


--
-- Name: reserva_locativa_objeto id_reserva_locativa_objeto; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.reserva_locativa_objeto ALTER COLUMN id_reserva_locativa_objeto SET DEFAULT nextval('public.reserva_locativa_objeto_id_seq'::regclass);


--
-- Name: reserva_locativa_objeto reserva_locativa_objeto_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.reserva_locativa_objeto
    ADD CONSTRAINT reserva_locativa_objeto_pkey PRIMARY KEY (id_reserva_locativa_objeto);


--
-- Name: reserva_locativa_objeto uq_rlo_uid_global; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.reserva_locativa_objeto
    ADD CONSTRAINT uq_rlo_uid_global UNIQUE (uid_global);


--
-- Name: idx_rlo_uid_global; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_rlo_uid_global ON public.reserva_locativa_objeto USING btree (uid_global);


--
-- Name: idx_rlo_reserva; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_rlo_reserva ON public.reserva_locativa_objeto USING btree (id_reserva_locativa);


--
-- Name: idx_rlo_inmueble; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_rlo_inmueble ON public.reserva_locativa_objeto USING btree (id_inmueble);


--
-- Name: idx_rlo_unidad; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_rlo_unidad ON public.reserva_locativa_objeto USING btree (id_unidad_funcional);


--
-- Name: uq_rlo_reserva_inmueble; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_rlo_reserva_inmueble ON public.reserva_locativa_objeto USING btree (id_reserva_locativa, id_inmueble) WHERE ((deleted_at IS NULL) AND (id_inmueble IS NOT NULL));


--
-- Name: uq_rlo_reserva_unidad; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uq_rlo_reserva_unidad ON public.reserva_locativa_objeto USING btree (id_reserva_locativa, id_unidad_funcional) WHERE ((deleted_at IS NULL) AND (id_unidad_funcional IS NOT NULL));


--
-- Name: reserva_locativa_objeto fk_rlo_reserva; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.reserva_locativa_objeto
    ADD CONSTRAINT fk_rlo_reserva FOREIGN KEY (id_reserva_locativa) REFERENCES public.reserva_locativa(id_reserva_locativa) ON DELETE RESTRICT;


--
-- Name: reserva_locativa_objeto fk_rlo_inmueble; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.reserva_locativa_objeto
    ADD CONSTRAINT fk_rlo_inmueble FOREIGN KEY (id_inmueble) REFERENCES public.inmueble(id_inmueble) ON DELETE RESTRICT;


--
-- Name: reserva_locativa_objeto fk_rlo_unidad; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.reserva_locativa_objeto
    ADD CONSTRAINT fk_rlo_unidad FOREIGN KEY (id_unidad_funcional) REFERENCES public.unidad_funcional(id_unidad_funcional) ON DELETE RESTRICT;


--
-- PostgreSQL database dump complete
--

\unrestrict SvGuuWBELfRzzBtgZiWG8D2cOqEd41CZoOjTpudlYg4WzHEUe94dZUATbwf7HZA
