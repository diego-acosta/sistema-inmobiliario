-- Seed DEV/demo idempotente de indices financieros.
-- Valores ficticios para pruebas manuales: NO son datos oficiales ni deben usarse en produccion.

WITH indices_demo AS (
    SELECT *
    FROM (VALUES
        (
            'CAC_DEMO',
            'CAC demo',
            'INDICE_DEMO',
            'PUNTOS',
            'MENSUAL',
            'DEV/demo',
            'ACTIVO',
            'VALORES DEMO NO OFICIALES. Seed tecnico para pruebas manuales DEV/demo.'
        ),
        (
            'IPC_DEMO',
            'IPC demo',
            'INDICE_DEMO',
            'PUNTOS',
            'MENSUAL',
            'DEV/demo',
            'ACTIVO',
            'VALORES DEMO NO OFICIALES. Seed tecnico para pruebas manuales DEV/demo.'
        ),
        (
            'UVA_DEMO',
            'UVA demo',
            'UNIDAD_VALOR_DEMO',
            'PESOS',
            'MENSUAL',
            'DEV/demo',
            'ACTIVO',
            'VALORES DEMO NO OFICIALES. Seed tecnico para pruebas manuales DEV/demo.'
        ),
        (
            'RIPTE_DEMO',
            'RIPTE demo',
            'INDICE_DEMO',
            'PUNTOS',
            'MENSUAL',
            'DEV/demo',
            'ACTIVO',
            'VALORES DEMO NO OFICIALES. Seed tecnico para pruebas manuales DEV/demo.'
        )
    ) AS t (
        codigo_indice_financiero,
        nombre_indice_financiero,
        tipo_indice,
        unidad_medida,
        frecuencia_publicacion,
        fuente_indice,
        estado_indice_financiero,
        observaciones
    )
)
INSERT INTO public.indice_financiero (
    codigo_indice_financiero,
    nombre_indice_financiero,
    tipo_indice,
    unidad_medida,
    frecuencia_publicacion,
    fuente_indice,
    estado_indice_financiero,
    observaciones
)
SELECT
    codigo_indice_financiero,
    nombre_indice_financiero,
    tipo_indice,
    unidad_medida,
    frecuencia_publicacion,
    fuente_indice,
    estado_indice_financiero,
    observaciones
FROM indices_demo
ON CONFLICT (codigo_indice_financiero) WHERE deleted_at IS NULL
DO UPDATE SET
    nombre_indice_financiero = EXCLUDED.nombre_indice_financiero,
    tipo_indice = EXCLUDED.tipo_indice,
    unidad_medida = EXCLUDED.unidad_medida,
    frecuencia_publicacion = EXCLUDED.frecuencia_publicacion,
    fuente_indice = EXCLUDED.fuente_indice,
    estado_indice_financiero = EXCLUDED.estado_indice_financiero,
    observaciones = EXCLUDED.observaciones
WHERE public.indice_financiero.nombre_indice_financiero IS DISTINCT FROM EXCLUDED.nombre_indice_financiero
   OR public.indice_financiero.tipo_indice IS DISTINCT FROM EXCLUDED.tipo_indice
   OR public.indice_financiero.unidad_medida IS DISTINCT FROM EXCLUDED.unidad_medida
   OR public.indice_financiero.frecuencia_publicacion IS DISTINCT FROM EXCLUDED.frecuencia_publicacion
   OR public.indice_financiero.fuente_indice IS DISTINCT FROM EXCLUDED.fuente_indice
   OR public.indice_financiero.estado_indice_financiero IS DISTINCT FROM EXCLUDED.estado_indice_financiero
   OR public.indice_financiero.observaciones IS DISTINCT FROM EXCLUDED.observaciones;

WITH valores_demo AS (
    SELECT *
    FROM (VALUES
        ('CAC_DEMO', DATE '2026-01-01', 1000.00000000, DATE '2026-01-10'),
        ('CAC_DEMO', DATE '2026-02-01', 1025.00000000, DATE '2026-02-10'),
        ('CAC_DEMO', DATE '2026-03-01', 1051.50000000, DATE '2026-03-10'),
        ('CAC_DEMO', DATE '2026-04-01', 1078.80000000, DATE '2026-04-10'),
        ('CAC_DEMO', DATE '2026-05-01', 1106.85000000, DATE '2026-05-10'),
        ('CAC_DEMO', DATE '2026-06-01', 1135.62000000, DATE '2026-06-10'),
        ('IPC_DEMO', DATE '2026-01-01', 100.00000000, DATE '2026-01-12'),
        ('IPC_DEMO', DATE '2026-02-01', 103.10000000, DATE '2026-02-12'),
        ('IPC_DEMO', DATE '2026-03-01', 106.40000000, DATE '2026-03-12'),
        ('IPC_DEMO', DATE '2026-04-01', 109.85000000, DATE '2026-04-12'),
        ('IPC_DEMO', DATE '2026-05-01', 113.48000000, DATE '2026-05-12'),
        ('IPC_DEMO', DATE '2026-06-01', 117.22000000, DATE '2026-06-12'),
        ('UVA_DEMO', DATE '2026-01-01', 500.00000000, DATE '2026-01-05'),
        ('UVA_DEMO', DATE '2026-02-01', 515.50000000, DATE '2026-02-05'),
        ('UVA_DEMO', DATE '2026-03-01', 532.00000000, DATE '2026-03-05'),
        ('UVA_DEMO', DATE '2026-04-01', 549.25000000, DATE '2026-04-05'),
        ('UVA_DEMO', DATE '2026-05-01', 567.42000000, DATE '2026-05-05'),
        ('UVA_DEMO', DATE '2026-06-01', 586.15000000, DATE '2026-06-05'),
        ('RIPTE_DEMO', DATE '2026-01-01', 750.00000000, DATE '2026-01-20'),
        ('RIPTE_DEMO', DATE '2026-02-01', 768.75000000, DATE '2026-02-20'),
        ('RIPTE_DEMO', DATE '2026-03-01', 789.12000000, DATE '2026-03-20'),
        ('RIPTE_DEMO', DATE '2026-04-01', 810.82000000, DATE '2026-04-20'),
        ('RIPTE_DEMO', DATE '2026-05-01', 833.55000000, DATE '2026-05-20'),
        ('RIPTE_DEMO', DATE '2026-06-01', 857.30000000, DATE '2026-06-20')
    ) AS t (
        codigo_indice_financiero,
        fecha_valor,
        valor_indice,
        fecha_publicacion
    )
), valores_resueltos AS (
    SELECT
        i.id_indice_financiero,
        v.fecha_valor,
        v.valor_indice,
        v.fecha_publicacion,
        'DEV/demo' AS fuente_valor,
        'PUBLICADO' AS estado_valor_indice,
        'VALOR DEMO NO OFICIAL. Seed tecnico para pruebas manuales DEV/demo.' AS observaciones
    FROM valores_demo v
    JOIN public.indice_financiero i
      ON i.codigo_indice_financiero = v.codigo_indice_financiero
     AND i.deleted_at IS NULL
)
INSERT INTO public.indice_financiero_valor (
    id_indice_financiero,
    fecha_valor,
    valor_indice,
    fecha_publicacion,
    fuente_valor,
    estado_valor_indice,
    observaciones
)
SELECT
    id_indice_financiero,
    fecha_valor,
    valor_indice,
    fecha_publicacion,
    fuente_valor,
    estado_valor_indice,
    observaciones
FROM valores_resueltos
ON CONFLICT (id_indice_financiero, fecha_valor) WHERE deleted_at IS NULL
DO UPDATE SET
    valor_indice = EXCLUDED.valor_indice,
    fecha_publicacion = EXCLUDED.fecha_publicacion,
    fuente_valor = EXCLUDED.fuente_valor,
    estado_valor_indice = EXCLUDED.estado_valor_indice,
    observaciones = EXCLUDED.observaciones
WHERE public.indice_financiero_valor.valor_indice IS DISTINCT FROM EXCLUDED.valor_indice
   OR public.indice_financiero_valor.fecha_publicacion IS DISTINCT FROM EXCLUDED.fecha_publicacion
   OR public.indice_financiero_valor.fuente_valor IS DISTINCT FROM EXCLUDED.fuente_valor
   OR public.indice_financiero_valor.estado_valor_indice IS DISTINCT FROM EXCLUDED.estado_valor_indice
   OR public.indice_financiero_valor.observaciones IS DISTINCT FROM EXCLUDED.observaciones;
