-- Patch idempotente: habilita FACTURA_SERVICIO como origen de relacion_generadora.

CREATE OR REPLACE FUNCTION public.trg_relacion_generadora_polimorfica() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    IF NEW.tipo_origen NOT IN ('venta', 'contrato_alquiler', 'factura_servicio') THEN
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
        WHEN 'factura_servicio' THEN
            IF NOT EXISTS (
                SELECT 1
                FROM factura_servicio
                WHERE id_factura_servicio = NEW.id_origen
                  AND deleted_at IS NULL
            ) THEN
                RAISE EXCEPTION 'relacion_generadora referencia factura_servicio inexistente: %', NEW.id_origen;
            END IF;
    END CASE;

    RETURN NEW;
END;
$$;
