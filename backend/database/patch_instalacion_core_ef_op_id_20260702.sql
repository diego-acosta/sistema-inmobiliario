CREATE UNIQUE INDEX IF NOT EXISTS ux_instalacion_op_id_alta
    ON public.instalacion (op_id_alta)
    WHERE op_id_alta IS NOT NULL;
