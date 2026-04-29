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

INSERT INTO public.concepto_financiero (
    codigo_concepto_financiero,
    nombre_concepto_financiero,
    descripcion_concepto_financiero,
    tipo_concepto_financiero,
    naturaleza_concepto,
    afecta_capital,
    afecta_interes,
    afecta_mora,
    afecta_impuesto,
    afecta_caja,
    es_imputable,
    permite_saldo,
    estado_concepto_financiero,
    observaciones
)
VALUES
    ('CAPITAL_VENTA', 'Capital de venta', 'Componente de capital asociado a una venta.', 'CAPITAL', 'DEBITO', true, false, false, false, true, true, true, 'ACTIVO', 'Catalogo financiero base'),
    ('ANTICIPO_VENTA', 'Anticipo de venta', 'Anticipo financiero asociado a una venta.', 'CAPITAL', 'DEBITO', true, false, false, false, true, true, true, 'ACTIVO', 'Catalogo financiero base'),
    ('SALDO_EXTRAORDINARIO', 'Saldo extraordinario', 'Saldo extraordinario generado fuera del cronograma ordinario.', 'CAPITAL', 'DEBITO', true, false, false, false, true, true, true, 'ACTIVO', 'Catalogo financiero base'),
    ('CANON_LOCATIVO', 'Canon locativo', 'Canon periodico de contrato locativo.', 'CAPITAL', 'DEBITO', true, false, false, false, true, true, true, 'ACTIVO', 'Catalogo financiero base'),
    ('EXPENSA_TRASLADADA', 'Expensa trasladada', 'Expensa trasladada al obligado financiero.', 'TRASLADO', 'DEBITO', false, false, false, false, true, true, true, 'ACTIVO', 'Catalogo financiero base'),
    ('SERVICIO_TRASLADADO', 'Servicio trasladado', 'Servicio trasladado al obligado financiero.', 'TRASLADO', 'DEBITO', false, false, false, false, true, true, true, 'ACTIVO', 'Catalogo financiero base'),
    ('IMPUESTO_TRASLADADO', 'Impuesto trasladado', 'Impuesto trasladado al obligado financiero.', 'TRASLADO', 'DEBITO', false, false, false, true, true, true, true, 'ACTIVO', 'Catalogo financiero base'),
    ('INTERES_FINANCIERO', 'Interes financiero', 'Interes financiero ordinario.', 'INTERES', 'DEBITO', false, true, false, false, true, true, true, 'ACTIVO', 'Catalogo financiero base'),
    ('INTERES_MORA', 'Interes de mora', 'Interes generado por mora.', 'MORA', 'DEBITO', false, true, true, false, true, true, true, 'ACTIVO', 'Catalogo financiero base'),
    ('PUNITORIO', 'Punitorio', 'Cargo punitorio por incumplimiento.', 'MORA', 'DEBITO', false, false, true, false, true, true, true, 'ACTIVO', 'Catalogo financiero base'),
    ('CARGO_ADMINISTRATIVO', 'Cargo administrativo', 'Cargo administrativo financiero.', 'CARGO', 'DEBITO', false, false, false, false, true, true, true, 'ACTIVO', 'Catalogo financiero base'),
    ('LIQUIDACION_FINAL', 'Liquidacion final', 'Componente de liquidacion final.', 'CIERRE', 'DEBITO', false, false, false, false, true, true, true, 'ACTIVO', 'Catalogo financiero base'),
    ('REFINANCIACION', 'Refinanciacion', 'Componente asociado a refinanciacion.', 'REFINANCIACION', 'DEBITO', false, false, false, false, true, true, true, 'ACTIVO', 'Catalogo financiero base'),
    ('CANCELACION_ANTICIPADA', 'Cancelacion anticipada', 'Componente asociado a cancelacion anticipada.', 'CIERRE', 'DEBITO', false, false, false, false, true, true, true, 'ACTIVO', 'Catalogo financiero base'),
    ('AJUSTE_INDEXACION', 'Ajuste por indexacion', 'Ajuste financiero por indice o actualizacion.', 'AJUSTE', 'DEBITO', false, false, false, false, true, true, true, 'ACTIVO', 'Catalogo financiero base'),
    ('CREDITO_MANUAL', 'Credito manual', 'Credito manual documentado.', 'AJUSTE', 'CREDITO', false, false, false, false, false, true, true, 'ACTIVO', 'Catalogo financiero base'),
    ('DEBITO_MANUAL', 'Debito manual', 'Debito manual documentado.', 'AJUSTE', 'DEBITO', false, false, false, false, true, true, true, 'ACTIVO', 'Catalogo financiero base')
ON CONFLICT (codigo_concepto_financiero) DO UPDATE SET
    nombre_concepto_financiero = EXCLUDED.nombre_concepto_financiero,
    descripcion_concepto_financiero = EXCLUDED.descripcion_concepto_financiero,
    tipo_concepto_financiero = EXCLUDED.tipo_concepto_financiero,
    naturaleza_concepto = EXCLUDED.naturaleza_concepto,
    afecta_capital = EXCLUDED.afecta_capital,
    afecta_interes = EXCLUDED.afecta_interes,
    afecta_mora = EXCLUDED.afecta_mora,
    afecta_impuesto = EXCLUDED.afecta_impuesto,
    afecta_caja = EXCLUDED.afecta_caja,
    es_imputable = EXCLUDED.es_imputable,
    permite_saldo = EXCLUDED.permite_saldo,
    estado_concepto_financiero = EXCLUDED.estado_concepto_financiero,
    observaciones = EXCLUDED.observaciones;

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
