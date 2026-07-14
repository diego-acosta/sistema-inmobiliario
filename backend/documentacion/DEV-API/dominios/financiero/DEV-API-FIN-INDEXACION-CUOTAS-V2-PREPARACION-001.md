# DEV-API-FIN — Preparación de corridas de indexación de cuotas V2

## Auditoría de flujo real

- Publicar un índice, según el modelo SQL vigente, significa persistir un registro en `indice_financiero_valor` con `estado_valor_indice = 'PUBLICADO'` y `fecha_publicacion` informada.
- El período aplicable del valor publicado está dado por `indice_financiero_valor.fecha_valor`; ese valor físico queda registrado en `id_indice_financiero_valor_aplicado` de la corrida ordinaria.
- La preparación automática deriva `fecha_corte` como el último día calendario del mes de `fecha_valor`. Esta normalización sigue el uso mensual vigente del preview V2, donde `periodo_aplicado` identifica el mes y `fecha_corte` delimita las obligaciones incluidas.
- La selección de configuraciones alcanzadas se restringe a `plan_pago_venta_bloque_indexacion` activo (`deleted_at IS NULL`) con el mismo `id_indice_financiero`, bloque y plan no eliminados, y `fecha_base_indice <= fecha_valor`.
- La preparación no modifica deuda, saldos, composiciones ni obligaciones; solo crea corridas `corrida_indexacion_financiera` en estado `PREVISUALIZADA` y sus detalles mediante el servicio de preview V2 existente.

## Regla mensual ordinaria

Para cada configuración de indexación existe como máximo una corrida automática ordinaria por índice y período. Una modificación posterior del índice no genera otra corrida ordinaria; pertenece a un flujo futuro de corrección/rectificación fuera de este PR.

La clave funcional ordinaria es:

- `id_plan_pago_venta`
- `id_plan_pago_venta_bloque`
- `id_plan_pago_venta_bloque_indexacion`
- `id_indice_financiero`
- `id_indice_financiero_valor_aplicado`
- `periodo_aplicado`
- `origen_corrida = PUBLICACION_INDICE`

## Punto de integración

No se detectó un endpoint funcional existente de publicación de valores de índice ni un consumidor específico para este evento. Por eso se expone un endpoint técnico:

`POST /api/v1/financiero/indexacion-cuotas-v2/valores-indice/{id_indice_financiero_valor}/preparar-corridas`

Clasificación CORE-EF: `COMMAND_WRITE_TECNICO`.

Headers requeridos: `X-Op-Id`, `X-Usuario-Id`, `X-Sucursal-Id`, `X-Instalacion-Id`. `If-Match-Version` no aplica porque no modifica una entidad versionada existente; crea/reusa corridas por clave funcional.

El request no acepta `fecha_corte`; el cliente no puede alterar el alcance temporal automático para generar otra corrida ordinaria.

## Separación publicación / preparación / aplicación

La publicación del índice no aplica deuda. La preparación es una transacción técnica separada que invoca previews persistidos con `origen_corrida = 'PUBLICACION_INDICE'`. La aplicación sigue dependiendo exclusivamente del endpoint de aplicación V2 de corridas.

## Idempotencia y concurrencia

- Idempotencia funcional: antes de crear, se busca una corrida activa existente por la clave ordinaria mensual.
- Idempotencia física: el índice único parcial `ux_cif_publicacion_indice_grupo_activo` impide dos corridas activas `PUBLICACION_INDICE` para la misma clave funcional.
- Recuperación concurrente: si dos requests compiten y la base devuelve unique violation de `ux_cif_publicacion_indice_grupo_activo`, se hace rollback, se consulta la corrida ganadora y se devuelve como `EXISTENTE`.
- Otras violaciones de integridad se reportan como `ERROR_INTEGRIDAD_PREPARACION_CORRIDA`; no se interpretan como idempotencia.

## X-Op-Id raíz

El servicio deriva un `op_id` por grupo a partir del `X-Op-Id` raíz para no reutilizar el mismo identificador técnico en varias corridas. No existe una tabla/lote físico que persista el `X-Op-Id` raíz y su payload completo; por eso la idempotencia garantizada por este PR es funcional por grupo y física por clave ordinaria mensual, no idempotencia total de lote por `X-Op-Id` raíz.

## Política de errores

- Error global: valor inexistente o no publicado (`VALOR_INDICE_PUBLICADO_INEXISTENTE`).
- Error por grupo: errores del preview V2. El lote continúa y reporta el error controlado por grupo.
- Carrera concurrente esperable: se recupera como existente; no debe escapar como 500.

## Evento

No se agrega un evento nuevo en este incremento. La publicación del índice queda separada de este proceso porque no existe endpoint de publicación auditado en la implementación actual; la preparación reutiliza la persistencia de preview V2 sin aplicar deuda.

## Limitaciones

No implementa motor de jobs, corrección de índices, reversión, alquileres, actualización de deuda ni aplicación automática.
