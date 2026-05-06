BEGIN;

INSERT INTO public.concepto_financiero (
    codigo_concepto_financiero,
    nombre_concepto_financiero,
    descripcion_concepto_financiero,
    tipo_concepto_financiero,
    naturaleza_concepto,
    afecta_capital,
    afecta_interes,
    afecta_mora,
    aplica_punitorio,
    afecta_impuesto,
    afecta_caja,
    es_imputable,
    permite_saldo,
    estado_concepto_financiero,
    observaciones
)
VALUES (
    'SERVICIO_RECUPERADO',
    'Servicio recuperado',
    'Recupero de servicio comun pagado por la empresa.',
    'TRASLADO',
    'DEBITO',
    false,
    false,
    false,
    true,
    false,
    true,
    true,
    true,
    'ACTIVO',
    'Catalogo financiero base'
)
ON CONFLICT (codigo_concepto_financiero) DO UPDATE SET
    nombre_concepto_financiero = EXCLUDED.nombre_concepto_financiero,
    descripcion_concepto_financiero = EXCLUDED.descripcion_concepto_financiero,
    tipo_concepto_financiero = EXCLUDED.tipo_concepto_financiero,
    naturaleza_concepto = EXCLUDED.naturaleza_concepto,
    afecta_capital = EXCLUDED.afecta_capital,
    afecta_interes = EXCLUDED.afecta_interes,
    afecta_mora = EXCLUDED.afecta_mora,
    aplica_punitorio = EXCLUDED.aplica_punitorio,
    afecta_impuesto = EXCLUDED.afecta_impuesto,
    afecta_caja = EXCLUDED.afecta_caja,
    es_imputable = EXCLUDED.es_imputable,
    permite_saldo = EXCLUDED.permite_saldo,
    estado_concepto_financiero = EXCLUDED.estado_concepto_financiero,
    observaciones = EXCLUDED.observaciones;

COMMIT;
