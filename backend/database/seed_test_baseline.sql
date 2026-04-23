-- BASELINE TECNICO MINIMO REUTILIZABLE
-- No representa datos de negocio.
-- reset_db.bat lo aplica en dev y test para asegurar
-- sucursal/instalacion base usadas por headers y metadata operativa.

INSERT INTO public.sucursal (
    id_sucursal,
    codigo_sucursal,
    nombre_sucursal,
    descripcion_sucursal,
    estado_sucursal,
    es_casa_central,
    permite_operacion,
    observaciones
)
VALUES (
    1,
    'SUC-TEST-001',
    'Sucursal Test',
    'Baseline tecnico de test',
    'ACTIVA',
    true,
    true,
    'Baseline tecnico para pytest'
)
ON CONFLICT (id_sucursal) DO NOTHING;

INSERT INTO public.instalacion (
    id_instalacion,
    id_sucursal,
    codigo_instalacion,
    nombre_instalacion,
    descripcion_instalacion,
    estado_instalacion,
    es_principal,
    permite_sincronizacion,
    observaciones
)
VALUES (
    1,
    1,
    'INST-TEST-001',
    'Instalacion Test',
    'Baseline tecnico de test',
    'ACTIVA',
    true,
    true,
    'Baseline tecnico para pytest'
)
ON CONFLICT (id_instalacion) DO NOTHING;

SELECT setval(
    'public.sucursal_id_sucursal_seq',
    GREATEST((SELECT COALESCE(MAX(id_sucursal), 1) FROM public.sucursal), 1),
    true
);

SELECT setval(
    'public.instalacion_id_instalacion_seq',
    GREATEST((SELECT COALESCE(MAX(id_instalacion), 1) FROM public.instalacion), 1),
    true
);
