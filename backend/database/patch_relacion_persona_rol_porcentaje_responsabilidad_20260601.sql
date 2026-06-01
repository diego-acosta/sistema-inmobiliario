-- Patch idempotente: porcentaje de responsabilidad de compradores en venta completa.
--
-- Alcance:
-- - Agrega fuente persistida opcional para responsabilidad financiera en
--   relacion_persona_rol, estructura soporte persona/rol/contexto venta.
-- - No obliga datos historicos ni exige suma 100 por SQL; la regla de negocio
--   queda en servicios/repositorios del dominio comercial.
-- - Permite copiar la misma fuente desde reserva_venta cuando exista.

ALTER TABLE public.relacion_persona_rol
    ADD COLUMN IF NOT EXISTS porcentaje_responsabilidad NUMERIC(5,2) NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
          FROM pg_constraint
         WHERE conrelid = 'public.relacion_persona_rol'::regclass
           AND conname = 'chk_rpr_porcentaje_responsabilidad'
    ) THEN
        ALTER TABLE public.relacion_persona_rol
            ADD CONSTRAINT chk_rpr_porcentaje_responsabilidad
            CHECK (
                porcentaje_responsabilidad IS NULL
                OR (
                    porcentaje_responsabilidad > 0
                    AND porcentaje_responsabilidad <= 100
                )
            );
    END IF;
END $$;
