-- Índice funcional parcial no destructivo para búsquedas batch normalizadas
-- del preview de importación de inmuebles.
CREATE INDEX IF NOT EXISTS ix_inmueble_codigo_normalizado_activo
ON public.inmueble (lower(btrim(codigo_inmueble)))
WHERE deleted_at IS NULL;
