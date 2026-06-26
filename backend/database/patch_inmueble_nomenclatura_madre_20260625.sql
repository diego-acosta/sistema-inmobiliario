-- patch_inmueble_nomenclatura_madre_20260625.sql
-- Issue #231: agrega nomenclatura madre opcional al dato catastral/registral del inmueble.

ALTER TABLE IF EXISTS public.inmueble_dato_catastral_registral
    ADD COLUMN IF NOT EXISTS nomenclatura_madre character varying(120);
