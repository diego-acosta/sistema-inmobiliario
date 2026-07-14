# DEV-API-FIN — Preparación de corridas de indexación de cuotas V2

## Auditoría de flujo real

- Publicar un índice, según el modelo SQL vigente, significa persistir un registro en `indice_financiero_valor` con `estado_valor_indice = 'PUBLICADO'` y `fecha_publicacion` informada.
- Una publicación válida exige simultáneamente `estado_valor_indice = 'PUBLICADO'` y `fecha_publicacion IS NOT NULL`; una fila incompleta no se corrige automáticamente ni permite preparar corridas.
- `periodo_aplicado` se normaliza al primer día del mes de `indice_financiero_valor.fecha_valor`; el valor físico utilizado queda registrado en `id_indice_financiero_valor_aplicado`.
- La preparación automática deriva `fecha_corte` como el último día calendario de ese mismo mes. El cliente no puede configurarla.
- La selección de configuraciones alcanzadas se restringe a `plan_pago_venta_bloque_indexacion` activo (`deleted_at IS NULL`) con el mismo `id_indice_financiero`, bloque y plan no eliminados. La elegibilidad compara `fecha_base_indice` contra la fecha física original `fecha_valor`; la normalización mensual se usa únicamente para `periodo_aplicado` y su identidad.
- La preparación no modifica deuda, saldos, composiciones ni obligaciones; solo crea corridas `corrida_indexacion_financiera` en estado `PREVISUALIZADA` y sus detalles mediante el servicio de preview V2 existente.

## Regla mensual ordinaria

Para cada configuración de indexación existe como máximo una corrida automática ordinaria por índice y mes. Otro valor publicado del mismo índice y mes no crea ni reemplaza una corrida: se informa `REQUIERE_CORRECCION` con `PERIODO_ORDINARIO_YA_PREPARADO_CON_OTRO_VALOR`. La corrección queda fuera de este incremento.

La clave funcional ordinaria es:

- `id_plan_pago_venta`
- `id_plan_pago_venta_bloque`
- `id_plan_pago_venta_bloque_indexacion`
- `id_indice_financiero`
- `periodo_aplicado`
- `origen_corrida = PUBLICACION_INDICE`

`id_indice_financiero_valor_aplicado` no integra la identidad mensual, pero conserva la referencia exacta al valor usado por la corrida.

La protección física usa el índice único parcial por expresión `date_trunc('month', periodo_aplicado::timestamp)`. Aunque una ruta defectuosa intente persistir otro día del mismo mes, PostgreSQL lo considera la misma identidad ordinaria y rechaza la segunda corrida `PUBLICACION_INDICE` activa.

La búsqueda funcional de una corrida existente usa el rango mensual semiabierto desde el primer día incluido hasta el primer día del mes siguiente excluido. El servicio persiste normalmente el primer día, pero tolera corridas históricas, importadas o sincronizadas con cualquier otro día del mismo mes y las considera la misma identidad ordinaria.

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
- Recuperación concurrente: si dos requests compiten y la base devuelve unique violation de `ux_cif_publicacion_indice_grupo_activo`, se hace rollback y se recarga la corrida ganadora con la misma búsqueda por rango mensual, incluso si quedó persistida con otro día del mes. Se devuelve `EXISTENTE` si usó el mismo valor o `REQUIERE_CORRECCION` si usó otro valor del mes.
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
