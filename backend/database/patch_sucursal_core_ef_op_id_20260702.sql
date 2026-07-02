CREATE UNIQUE INDEX IF NOT EXISTS ux_sucursal_op_id_alta
    ON public.sucursal (op_id_alta)
    WHERE op_id_alta IS NOT NULL;
