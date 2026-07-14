-- Patch idempotente: idempotencia física de preparación automática de corridas V2 por publicación de índice.
-- No modifica deuda ni aplica corridas.
-- Regla: una sola corrida ordinaria automática activa por configuración, índice y mes.

DROP INDEX IF EXISTS public.ux_cif_publicacion_indice_grupo_activo;

CREATE UNIQUE INDEX ux_cif_publicacion_indice_grupo_activo
    ON public.corrida_indexacion_financiera (
        id_plan_pago_venta,
        id_plan_pago_venta_bloque,
        id_plan_pago_venta_bloque_indexacion,
        id_indice_financiero,
        (date_trunc('month', periodo_aplicado::timestamp)),
        origen_corrida
    )
    WHERE deleted_at IS NULL
      AND origen_corrida = 'PUBLICACION_INDICE'
      AND estado_corrida NOT IN ('ANULADA','REEMPLAZADA');
