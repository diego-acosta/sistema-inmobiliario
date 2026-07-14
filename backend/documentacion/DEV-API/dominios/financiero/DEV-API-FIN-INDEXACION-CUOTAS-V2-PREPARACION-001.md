# DEV-API-FIN — Preparación de corridas de indexación de cuotas V2

## Auditoría de flujo real

- Publicar un índice, según el modelo SQL vigente, significa persistir un registro en `indice_financiero_valor` con `estado_valor_indice = 'PUBLICADO'` y `fecha_publicacion` informada.
- El período aplicable del valor publicado está dado por `indice_financiero_valor.fecha_valor`.
- La selección de configuraciones alcanzadas se restringe a `plan_pago_venta_bloque_indexacion` activo (`deleted_at IS NULL`) con el mismo `id_indice_financiero`, bloque y plan no eliminados, y `fecha_base_indice <= fecha_valor`.
- La preparación no modifica deuda, saldos, composiciones ni obligaciones; solo crea corridas `corrida_indexacion_financiera` en estado `PREVISUALIZADA` y sus detalles mediante el servicio de preview V2 existente.
- La idempotencia física de preparación automática usa el índice único parcial `ux_cif_publicacion_indice_grupo_activo` por plan + bloque + configuración + índice + valor publicado + período + origen `PUBLICACION_INDICE`.

## Punto de integración

No se detectó un endpoint funcional existente de publicación de valores de índice ni un consumidor específico para este evento. Por eso se expone un endpoint técnico:

`POST /api/v1/financiero/indexacion-cuotas-v2/valores-indice/{id_indice_financiero_valor}/preparar-corridas`

Clasificación CORE-EF: `COMMAND_WRITE_TECNICO`.

Headers requeridos: `X-Op-Id`, `X-Usuario-Id`, `X-Sucursal-Id`, `X-Instalacion-Id`. `If-Match-Version` no aplica porque no modifica una entidad versionada existente; crea/reusa corridas por clave funcional.

## Separación publicación / preparación / aplicación

La publicación del índice no aplica deuda. La preparación es una transacción técnica separada que invoca previews persistidos con `origen_corrida = 'PUBLICACION_INDICE'`. La aplicación sigue dependiendo exclusivamente del endpoint de aplicación V2 de corridas.

## Agrupamiento e idempotencia

Se genera como máximo una corrida por:

- `id_plan_pago_venta`
- `id_plan_pago_venta_bloque`
- `id_plan_pago_venta_bloque_indexacion`
- `id_indice_financiero_valor_aplicado`
- `periodo_aplicado`

Si una corrida activa ya existe, se reporta como `EXISTENTE`. Si no hay obligaciones analizables, se reporta `SIN_OBLIGACIONES` sin crear corrida vacía.

## Política de errores

- Error global: valor inexistente o no publicado (`VALOR_INDICE_PUBLICADO_INEXISTENTE`).
- Error por grupo: errores del preview V2. El lote continúa y reporta el error controlado por grupo.

## Evento

No se agrega un evento nuevo en este incremento. La publicación del índice queda separada de este proceso porque no existe endpoint de publicación auditado en la implementación actual; la preparación reutiliza la persistencia de preview V2 sin aplicar deuda.

## Limitaciones

No implementa motor de jobs, reversión, alquileres, actualización de deuda ni aplicación automática.
