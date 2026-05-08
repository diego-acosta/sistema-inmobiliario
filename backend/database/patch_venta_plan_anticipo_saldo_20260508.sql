ALTER TABLE public.venta
ADD COLUMN IF NOT EXISTS tipo_plan_financiero character varying(30) NOT NULL DEFAULT 'CONTADO',
ADD COLUMN IF NOT EXISTS moneda character varying(10) NOT NULL DEFAULT 'ARS',
ADD COLUMN IF NOT EXISTS importe_anticipo numeric(14,2),
ADD COLUMN IF NOT EXISTS fecha_vencimiento_anticipo date,
ADD COLUMN IF NOT EXISTS importe_saldo numeric(14,2),
ADD COLUMN IF NOT EXISTS fecha_vencimiento_saldo date;

ALTER TABLE public.venta
DROP CONSTRAINT IF EXISTS chk_venta_tipo_plan_financiero;

ALTER TABLE public.venta
ADD CONSTRAINT chk_venta_tipo_plan_financiero
CHECK (tipo_plan_financiero IN ('CONTADO', 'ANTICIPO_Y_SALDO'));

ALTER TABLE public.venta
DROP CONSTRAINT IF EXISTS chk_venta_plan_contado_sin_detalle;

ALTER TABLE public.venta
ADD CONSTRAINT chk_venta_plan_contado_sin_detalle
CHECK (
    tipo_plan_financiero <> 'CONTADO'
    OR (
        importe_anticipo IS NULL
        AND fecha_vencimiento_anticipo IS NULL
        AND importe_saldo IS NULL
        AND fecha_vencimiento_saldo IS NULL
    )
);

ALTER TABLE public.venta
DROP CONSTRAINT IF EXISTS chk_venta_plan_anticipo_saldo_completo;

ALTER TABLE public.venta
ADD CONSTRAINT chk_venta_plan_anticipo_saldo_completo
CHECK (
    tipo_plan_financiero <> 'ANTICIPO_Y_SALDO'
    OR (
        monto_total IS NOT NULL
        AND importe_anticipo IS NOT NULL
        AND importe_anticipo > 0
        AND fecha_vencimiento_anticipo IS NOT NULL
        AND importe_saldo IS NOT NULL
        AND importe_saldo > 0
        AND fecha_vencimiento_saldo IS NOT NULL
        AND importe_anticipo + importe_saldo = monto_total
    )
);
