-- Patch: validacion de sobreaplicacion ignora aplicaciones soft-deleted
-- Fecha: 2026-05-05

CREATE OR REPLACE FUNCTION public.trg_aplicacion_financiera_validar_consistencia()
RETURNS trigger
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
           AND a.deleted_at IS NULL
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
       AND a.deleted_at IS NULL
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
