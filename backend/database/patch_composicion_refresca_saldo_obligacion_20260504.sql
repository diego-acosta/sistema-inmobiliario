-- Patch: saldos de obligacion derivados de composiciones activas
-- Fecha: 2026-05-04

CREATE OR REPLACE FUNCTION public.fn_refrescar_saldo_obligacion_desde_composiciones(
    p_id_obligacion_financiera bigint
) RETURNS void
    LANGUAGE plpgsql
    AS $$
BEGIN
    IF p_id_obligacion_financiera IS NULL THEN
        RETURN;
    END IF;

    UPDATE composicion_obligacion c
       SET saldo_componente = CASE
                WHEN c.deleted_at IS NULL
                 AND c.estado_composicion_obligacion = 'ACTIVA'
                THEN GREATEST(
                    0,
                    c.importe_componente - COALESCE((
                        SELECT SUM(a.importe_aplicado)
                        FROM aplicacion_financiera a
                        WHERE a.id_composicion_obligacion = c.id_composicion_obligacion
                          AND a.deleted_at IS NULL
                    ), 0)
                )
                ELSE 0
           END,
           updated_at = CURRENT_TIMESTAMP,
           version_registro = c.version_registro + 1
     WHERE c.id_obligacion_financiera = p_id_obligacion_financiera;

    UPDATE obligacion_financiera o
       SET importe_total = COALESCE((
                SELECT SUM(c.importe_componente)
                FROM composicion_obligacion c
                WHERE c.id_obligacion_financiera = o.id_obligacion_financiera
                  AND c.deleted_at IS NULL
                  AND c.estado_composicion_obligacion = 'ACTIVA'
           ), 0),
           saldo_pendiente = COALESCE((
                SELECT SUM(c.saldo_componente)
                FROM composicion_obligacion c
                WHERE c.id_obligacion_financiera = o.id_obligacion_financiera
                  AND c.deleted_at IS NULL
                  AND c.estado_composicion_obligacion = 'ACTIVA'
           ), 0),
           importe_cancelado_acumulado = COALESCE((
                SELECT SUM(a.importe_aplicado)
                FROM aplicacion_financiera a
                WHERE a.id_obligacion_financiera = o.id_obligacion_financiera
                  AND a.deleted_at IS NULL
           ), 0),
           updated_at = CURRENT_TIMESTAMP,
           version_registro = o.version_registro + 1
     WHERE o.id_obligacion_financiera = p_id_obligacion_financiera;
END;
$$;

CREATE OR REPLACE FUNCTION public.trg_aplicacion_financiera_refrescar_saldo_obligacion()
RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    IF TG_OP IN ('UPDATE', 'DELETE') THEN
        PERFORM public.fn_refrescar_saldo_obligacion_desde_composiciones(OLD.id_obligacion_financiera);
    END IF;

    IF TG_OP IN ('INSERT', 'UPDATE') THEN
        PERFORM public.fn_refrescar_saldo_obligacion_desde_composiciones(NEW.id_obligacion_financiera);
    END IF;

    RETURN COALESCE(NEW, OLD);
END;
$$;

CREATE OR REPLACE FUNCTION public.trg_composicion_obligacion_refrescar_saldo_obligacion()
RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    IF pg_trigger_depth() > 1 THEN
        RETURN COALESCE(NEW, OLD);
    END IF;

    IF TG_OP IN ('UPDATE', 'DELETE') THEN
        PERFORM public.fn_refrescar_saldo_obligacion_desde_composiciones(OLD.id_obligacion_financiera);
    END IF;

    IF TG_OP IN ('INSERT', 'UPDATE') THEN
        PERFORM public.fn_refrescar_saldo_obligacion_desde_composiciones(NEW.id_obligacion_financiera);
    END IF;

    RETURN COALESCE(NEW, OLD);
END;
$$;

CREATE OR REPLACE FUNCTION public.trg_composicion_obligacion_preparar_saldo_componente()
RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    IF NEW.deleted_at IS NOT NULL
       OR NEW.estado_composicion_obligacion <> 'ACTIVA' THEN
        NEW.saldo_componente := 0;
        RETURN NEW;
    END IF;

    NEW.saldo_componente := GREATEST(
        0,
        NEW.importe_componente - COALESCE((
            SELECT SUM(a.importe_aplicado)
            FROM aplicacion_financiera a
            WHERE a.id_composicion_obligacion = NEW.id_composicion_obligacion
              AND a.deleted_at IS NULL
        ), 0)
    );

    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_biu_composicion_obligacion_preparar_saldo_componente
    ON public.composicion_obligacion;

CREATE TRIGGER trg_biu_composicion_obligacion_preparar_saldo_componente
BEFORE INSERT OR UPDATE ON public.composicion_obligacion
FOR EACH ROW
EXECUTE FUNCTION public.trg_composicion_obligacion_preparar_saldo_componente();

DROP TRIGGER IF EXISTS trg_aiud_composicion_obligacion_refrescar_saldo_obligacion
    ON public.composicion_obligacion;

CREATE TRIGGER trg_aiud_composicion_obligacion_refrescar_saldo_obligacion
AFTER INSERT OR UPDATE OR DELETE ON public.composicion_obligacion
FOR EACH ROW
EXECUTE FUNCTION public.trg_composicion_obligacion_refrescar_saldo_obligacion();
