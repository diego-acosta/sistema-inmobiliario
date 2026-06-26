-- patch_inmueble_dcr_unico_no_eliminado_20260626.sql
-- Issue #232: garantiza atomicamente un unico dato catastral/registral
-- no eliminado por inmueble.
--
-- Diagnostico previo si el indice no pudiera crearse por datos heredados:
-- SELECT id_inmueble, COUNT(*) AS cantidad
-- FROM public.inmueble_dato_catastral_registral
-- WHERE deleted_at IS NULL
-- GROUP BY id_inmueble
-- HAVING COUNT(*) > 1;
--
-- Este patch no borra, cierra ni migra destructivamente datos existentes.

CREATE UNIQUE INDEX IF NOT EXISTS ux_inmueble_dcr_unico_no_eliminado
ON public.inmueble_dato_catastral_registral (id_inmueble)
WHERE deleted_at IS NULL;
